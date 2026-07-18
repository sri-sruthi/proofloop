"""Deterministic invoice policy boundary.

`evaluate_policy` is a pure function: identical inputs always yield the same
disposition. The LLM never participates here. `ACCEPT_FOR_POLICY_EVALUATION`
means "safe to hand to the next policy stage", NOT "approved for payment".
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_validator

from proofloop.agents._base import AgentModel
from proofloop.agents.contracts import (
    Disposition,
    DuplicateStatus,
    ExtractedInvoice,
    MismatchCategory,
    PolicyDecision,
    ReconciliationFindings,
)

_ACTION_BY_DISPOSITION = {
    Disposition.BLOCK: "Block this invoice and notify the accounts-payable owner with the reasons.",
    Disposition.HUMAN_REVIEW: "Route this invoice to a human reviewer before any policy or payment step.",
    Disposition.ACCEPT_FOR_POLICY_EVALUATION: "Forward to the next deterministic policy stage; this is not payment approval.",
}


class PolicyConfig(AgentModel):
    """Explicit, configurable thresholds — no hidden magic numbers."""

    amount_tolerance: Decimal = Field(default=Decimal("0.00"), ge=0)
    high_value_threshold: Decimal = Field(default=Decimal("10000.00"), gt=0)
    min_extraction_confidence: float = Field(default=0.70, ge=0.0, le=1.0)
    missing_po_disposition: Disposition = Disposition.HUMAN_REVIEW

    @field_validator("missing_po_disposition")
    @classmethod
    def missing_po_must_escalate_or_block(cls, value: Disposition) -> Disposition:
        if value is Disposition.ACCEPT_FOR_POLICY_EVALUATION:
            raise ValueError("a missing purchase order cannot be auto-accepted")
        return value


def evaluate_policy(
    *,
    extraction: ExtractedInvoice,
    findings: ReconciliationFindings,
    config: PolicyConfig,
) -> PolicyDecision:
    """Reduce extraction + reconciliation findings to a deterministic decision.

    Precedence: any BLOCK condition dominates any HUMAN_REVIEW condition, which
    dominates ACCEPT. Reasons and triggered rule ids are always populated so the
    customer never sees a black-box outcome.
    """

    reasons: list[str] = []
    rules: list[str] = []
    block = False
    escalate = False

    categories = {mismatch.category for mismatch in findings.mismatches}

    # --- BLOCK conditions ---
    if findings.duplicate_status is DuplicateStatus.CONFIRMED_DUPLICATE:
        block = True
        rules.append("DUPLICATE_BLOCK")
        reasons.append("Confirmed duplicate invoice.")
    if MismatchCategory.UNKNOWN_VENDOR in categories:
        block = True
        rules.append("UNKNOWN_VENDOR_BLOCK")
        reasons.append("Vendor is not in the approved vendor record.")

    # --- Missing purchase order: configurable block-or-review ---
    if MismatchCategory.PO_NOT_FOUND in categories:
        if config.missing_po_disposition is Disposition.BLOCK:
            block = True
            rules.append("MISSING_PO_BLOCK")
        else:
            escalate = True
            rules.append("MISSING_PO_REVIEW")
        reasons.append("No matching purchase order was found.")

    # --- HUMAN_REVIEW conditions ---
    if MismatchCategory.AMOUNT_MISMATCH in categories:
        escalate = True
        rules.append("AMOUNT_MISMATCH_REVIEW")
        reasons.append("Invoice total differs from the purchase order beyond tolerance.")
    if MismatchCategory.CURRENCY_MISMATCH in categories:
        escalate = True
        rules.append("CURRENCY_MISMATCH_REVIEW")
        reasons.append("Invoice currency differs from the purchase order currency.")
    if findings.duplicate_status is DuplicateStatus.SUSPECTED_DUPLICATE:
        escalate = True
        rules.append("SUSPECTED_DUPLICATE_REVIEW")
        reasons.append("Invoice looks like a possible duplicate.")

    confidence = extraction.model_reported_confidence
    if confidence is None or confidence < config.min_extraction_confidence:
        escalate = True
        rules.append("LOW_CONFIDENCE_REVIEW")
        reasons.append("Extraction confidence is missing or below the configured threshold.")

    if extraction.total >= config.high_value_threshold:
        escalate = True
        rules.append("HIGH_VALUE_REVIEW")
        reasons.append("Invoice total is at or above the high-value threshold.")

    if block:
        disposition = Disposition.BLOCK
    elif escalate:
        disposition = Disposition.HUMAN_REVIEW
    else:
        disposition = Disposition.ACCEPT_FOR_POLICY_EVALUATION
        reasons.append("No blocking or review condition was triggered.")

    return PolicyDecision(
        disposition=disposition,
        reasons=tuple(reasons),
        triggered_rules=tuple(rules),
        safe_next_action=_ACTION_BY_DISPOSITION[disposition],
    )
