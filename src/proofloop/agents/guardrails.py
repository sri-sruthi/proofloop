"""Deterministic, free guardrail middleware for the invoice agent slice.

This layer produces typed *control observations* — agent-neutral records that a
named safety control ran and what it concluded. They are deliberately NOT
ProofLoop ``EvidenceEnvelope`` objects: this package stays isolated from the
domain evidence contracts. A later composition root maps each observation onto a
requirement-bound evidence envelope (see ``ONE_DAY_AGENT_DELIVERY.md``).

Everything here is deterministic and offline. No paid service, model call, or
network access is involved. Raw PII is never stored in a log line, reason string,
or observation attribute — only bounded counts and kinds are retained.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import Field

from proofloop.agents._base import AgentModel, Identifier
from proofloop.agents.contracts import Disposition, InvoiceInput

GUARDRAIL_VERSION = "invoice-guardrail-v1"
COMPONENT = "proofloop.agents.guardrails"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ControlOutcome(str, Enum):
    """Outcome of a single deterministic control observation."""

    # B105 false positive: this is an assurance-outcome enum member, not a
    # password. The literal "PASS" is a serialization contract consumed by the
    # evidence bridge (ControlOutcome.value -> EvidenceOutcome) and must not
    # change; the suppression is scoped to this single line only.
    PASS = "PASS"  # nosec B105
    FAIL = "FAIL"
    UNAVAILABLE = "UNAVAILABLE"


class ControlKey(str, Enum):
    """Stable control keys mapped one-to-one onto evidence requirements later."""

    PII_REDACTION = "guardrail.pii_redaction"
    AUDIT_LOGGING = "guardrail.audit_logging"
    HITL_BOUNDARY = "guardrail.hitl_boundary"
    EXTRACTION_SCHEMA_VALIDATION = "guardrail.extraction_schema_validation"


class PiiKind(str, Enum):
    """The bounded set of PII this demo guardrail detects and redacts."""

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ACCOUNT_NUMBER = "ACCOUNT_NUMBER"


# --- PII detection ---------------------------------------------------------

# Bounded, deterministic patterns. Order matters: emails first, then phones,
# then bare account-like digit runs, each applied to already-redacted text so a
# value is never counted twice.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_ACCOUNT_RE = re.compile(r"\b\d{8,}\b")

_PLACEHOLDER = {
    PiiKind.EMAIL: "[REDACTED_EMAIL]",
    PiiKind.PHONE: "[REDACTED_PHONE]",
    PiiKind.ACCOUNT_NUMBER: "[REDACTED_ACCOUNT]",
}


class PiiFinding(AgentModel):
    """How many values of one PII kind were found — never the values."""

    kind: PiiKind
    count: int = Field(ge=1)


class RedactionOutcome(AgentModel):
    """Result of redacting untrusted text.

    ``redacted_text`` contains only placeholders; ``findings`` carry counts, not
    values. Nothing here can leak a raw email, phone, or account number.
    """

    redacted_text: str
    findings: tuple[PiiFinding, ...] = ()

    @property
    def total_redacted(self) -> int:
        return sum(finding.count for finding in self.findings)


def _looks_like_phone(candidate: str) -> bool:
    # Require at least 10 digits so invoice amounts / short codes are ignored,
    # and a separator or leading "+" so a bare digit run is treated as an
    # account number rather than a phone number.
    digits = sum(character.isdigit() for character in candidate)
    has_separator = any(character in " ().-" for character in candidate)
    return digits >= 10 and (has_separator or candidate.lstrip().startswith("+"))


def redact_pii(text: str) -> RedactionOutcome:
    """Deterministically redact a bounded set of PII from untrusted text."""

    counts: dict[PiiKind, int] = {}

    def _sub(pattern: re.Pattern[str], kind: PiiKind, source: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            if kind is PiiKind.PHONE and not _looks_like_phone(match.group(0)):
                return match.group(0)
            counts[kind] = counts.get(kind, 0) + 1
            return _PLACEHOLDER[kind]

        return pattern.sub(_replace, source)

    redacted = _sub(_EMAIL_RE, PiiKind.EMAIL, text)
    redacted = _sub(_PHONE_RE, PiiKind.PHONE, redacted)
    redacted = _sub(_ACCOUNT_RE, PiiKind.ACCOUNT_NUMBER, redacted)

    findings = tuple(
        PiiFinding(kind=kind, count=counts[kind])
        for kind in PiiKind
        if counts.get(kind)
    )
    return RedactionOutcome(redacted_text=redacted, findings=findings)


# --- Control observations --------------------------------------------------


class ControlAttribute(AgentModel):
    """One scalar, PII-free attribute attached to a control observation."""

    key: Identifier
    value: str | int | bool


class ControlObservation(AgentModel):
    """Agent-neutral record that one named safety control ran.

    This is intentionally *not* an ``EvidenceEnvelope``. It carries the stable
    control key, the outcome, an observation timestamp, the component/guardrail
    versions, a human-readable reason, and a safe next action — everything the
    composition root needs to emit a requirement-bound evidence event, without
    ever coupling this package to the domain.
    """

    control_key: ControlKey
    outcome: ControlOutcome
    observed_at: datetime
    component: Identifier
    guardrail_version: Identifier
    reason: Identifier
    safe_next_action: Identifier
    attributes: tuple[ControlAttribute, ...] = ()


class GuardrailMiddleware:
    """Deterministic guardrail controls for the invoice workflow.

    A ``now`` factory is injectable so tests are fully deterministic; production
    uses UTC wall-clock.
    """

    def __init__(self, *, version: str = GUARDRAIL_VERSION) -> None:
        self._version = version

    def _observe(
        self,
        *,
        control_key: ControlKey,
        outcome: ControlOutcome,
        reason: str,
        safe_next_action: str,
        now: datetime,
        attributes: tuple[ControlAttribute, ...] = (),
    ) -> ControlObservation:
        return ControlObservation(
            control_key=control_key,
            outcome=outcome,
            observed_at=now,
            component=COMPONENT,
            guardrail_version=self._version,
            reason=reason,
            safe_next_action=safe_next_action,
            attributes=attributes,
        )

    def observe_pii_redaction(
        self,
        *,
        invoice: InvoiceInput,
        now: datetime | None = None,
    ) -> tuple[ControlObservation, RedactionOutcome]:
        """Redact PII in the untrusted content and record the control ran.

        Only the untrusted content is scanned; trusted operator metadata is
        never merged into it. The observation stores counts only, so no raw PII
        can leak into evidence downstream.
        """

        moment = now or _utcnow()
        redaction = redact_pii(invoice.untrusted_content)
        attributes = tuple(
            ControlAttribute(key=f"{finding.kind.value.lower()}_redacted", value=finding.count)
            for finding in redaction.findings
        )
        reason = (
            f"Scanned untrusted invoice content; redacted {redaction.total_redacted} "
            "PII value(s) before any model call."
        )
        return (
            self._observe(
                control_key=ControlKey.PII_REDACTION,
                outcome=ControlOutcome.PASS,
                reason=reason,
                safe_next_action="Proceed with the redacted content; raw PII is not persisted.",
                now=moment,
                attributes=attributes,
            ),
            redaction,
        )

    def observe_audit_logging(
        self,
        *,
        document_id: str,
        action: str,
        now: datetime | None = None,
    ) -> ControlObservation:
        """Record that an append-only, PII-free audit line was produced."""

        moment = now or _utcnow()
        return self._observe(
            control_key=ControlKey.AUDIT_LOGGING,
            outcome=ControlOutcome.PASS,
            reason=f"Audit line recorded for document {document_id}: {action}.",
            safe_next_action="Retain the audit line; it contains identifiers only, no raw PII.",
            now=moment,
            attributes=(ControlAttribute(key="action", value=action),),
        )

    def observe_extraction_schema_validation(
        self,
        *,
        validated: bool,
        detail: str,
        now: datetime | None = None,
    ) -> ControlObservation:
        """PASS when model output validated to the strict schema, else FAIL."""

        moment = now or _utcnow()
        outcome = ControlOutcome.PASS if validated else ControlOutcome.FAIL
        action = (
            "Continue; the extraction satisfied the strict invoice schema."
            if validated
            else "Route to a human reviewer; the model output failed schema validation."
        )
        return self._observe(
            control_key=ControlKey.EXTRACTION_SCHEMA_VALIDATION,
            outcome=outcome,
            reason=detail,
            safe_next_action=action,
            now=moment,
            attributes=(ControlAttribute(key="validated", value=validated),),
        )

    def observe_hitl_boundary(
        self,
        *,
        disposition: Disposition,
        routed_to_human: bool,
        now: datetime | None = None,
    ) -> ControlObservation:
        """Confirm uncertain/unsafe dispositions actually reached a human.

        ``HUMAN_REVIEW`` and ``BLOCK`` are consequential states that must engage a
        person. If such a state was not routed to human review, the control FAILs
        so the customer never silently loses the human boundary.
        """

        moment = now or _utcnow()
        needs_human = disposition in (Disposition.HUMAN_REVIEW, Disposition.BLOCK)
        if not needs_human:
            return self._observe(
                control_key=ControlKey.HITL_BOUNDARY,
                outcome=ControlOutcome.PASS,
                reason="Disposition did not require the human boundary.",
                safe_next_action="Proceed to the next deterministic policy stage; this is not payment approval.",
                now=moment,
                attributes=(ControlAttribute(key="routed_to_human", value=False),),
            )
        outcome = ControlOutcome.PASS if routed_to_human else ControlOutcome.FAIL
        reason = (
            f"{disposition.value} correctly routed to human review."
            if routed_to_human
            else f"{disposition.value} was NOT routed to a human; the boundary was breached."
        )
        action = (
            "Await the human decision; no payment can proceed automatically."
            if routed_to_human
            else "Escalate immediately: a consequential state bypassed the human boundary."
        )
        return self._observe(
            control_key=ControlKey.HITL_BOUNDARY,
            outcome=outcome,
            reason=reason,
            safe_next_action=action,
            now=moment,
            attributes=(ControlAttribute(key="routed_to_human", value=routed_to_human),),
        )
