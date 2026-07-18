"""Deterministic runtime evidence evaluator for ProofLoop."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from proofloop.domain.models import (
    AssuranceEvaluation,
    AssuranceStatus,
    ControlDefinition,
    EvidenceEnvelope,
    EvidenceOutcome,
    ReasonCode,
    RequiredEvidenceSpecification,
    StateTransitionExplanation,
    WorkflowExecutionReference,
)
from proofloop.domain.ports import Clock


_REASON_PRIORITY = {
    ReasonCode.CONTROL_FAILURE_OBSERVED: 10,
    ReasonCode.CLOCK_SKEW_EXCEEDED: 20,
    ReasonCode.EVIDENCE_CONFLICT: 30,
    ReasonCode.OBSOLETE_PROVENANCE: 40,
    ReasonCode.EVIDENCE_UNCORRELATED: 50,
    ReasonCode.REMEDIATION_UNVERIFIED: 60,
    ReasonCode.EVIDENCE_STALE: 70,
    ReasonCode.EVIDENCE_UNAVAILABLE: 80,
    ReasonCode.EVIDENCE_INCOMPLETE: 90,
    ReasonCode.REQUIRED_EVIDENCE_MISSING: 100,
    ReasonCode.NO_CONTROLS_DECLARED: 110,
    ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED: 120,
}
_REASON_TEXT = {
    ReasonCode.REQUIRED_EVIDENCE_MISSING: "required evidence is missing",
    ReasonCode.EVIDENCE_STALE: "the latest evidence is stale",
    ReasonCode.EVIDENCE_CONFLICT: "the latest evidence is conflicting",
    ReasonCode.EVIDENCE_INCOMPLETE: "the latest evidence is incomplete",
    ReasonCode.EVIDENCE_UNAVAILABLE: "the evidence source is unavailable",
    ReasonCode.EVIDENCE_UNCORRELATED: "evidence belongs to another execution",
    ReasonCode.OBSOLETE_PROVENANCE: "evidence uses obsolete provenance",
    ReasonCode.CONTROL_FAILURE_OBSERVED: "a current control failure was observed",
    ReasonCode.REMEDIATION_UNVERIFIED: "remediation lacks new verification evidence",
    ReasonCode.CLOCK_SKEW_EXCEEDED: "evidence clock skew exceeds the allowed tolerance",
    ReasonCode.NO_CONTROLS_DECLARED: "no required controls are declared",
}


_DeduplicationKey = tuple[str, str, str, str, str, str]


@dataclass(frozen=True)
class _Finding:
    """Internal result for one declared evidence requirement."""

    control: ControlDefinition
    status: AssuranceStatus
    reason: ReasonCode | None
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class _DeduplicatedEvidence:
    """Canonical evidence plus source-event collision metadata."""

    events: tuple[EvidenceEnvelope, ...]
    ignored_ids: tuple[str, ...]
    collision_keys: frozenset[_DeduplicationKey]


def evaluate_assurance(
    *,
    controls: Sequence[ControlDefinition],
    evidence: Sequence[EvidenceEnvelope],
    workflow: WorkflowExecutionReference,
    clock: Clock,
    previous_status: AssuranceStatus | None = None,
) -> AssuranceEvaluation:
    """Reduce declared controls and normalized evidence to one assurance state.

    The function is pure relative to the injected clock. It evaluates evidence by
    observation time, rejects ambiguous source-event reuse, and cannot produce
    GREEN unless every declared evidence requirement is currently supported.
    """

    evaluated_at = clock.now()
    _require_utc(evaluated_at)

    deduplicated = _deduplicate(evidence)
    ordered_controls = tuple(sorted(controls, key=lambda item: item.control_id))
    findings: list[_Finding] = []
    reason_codes: tuple[ReasonCode, ...]

    for control in ordered_controls:
        for requirement in sorted(
            control.required_evidence,
            key=lambda item: item.requirement_id,
        ):
            findings.append(
                _evaluate_requirement(
                    control=control,
                    requirement=requirement,
                    events=deduplicated.events,
                    collision_keys=deduplicated.collision_keys,
                    workflow=workflow,
                    evaluated_at=evaluated_at,
                )
            )

    if not findings:
        status = AssuranceStatus.AMBER
        reason_codes = (ReasonCode.NO_CONTROLS_DECLARED,)
        affected_control_ids: tuple[str, ...] = ()
        considered_ids: tuple[str, ...] = ()
        summary = "No required controls are declared, so assurance cannot be established."
        next_safe_action = "Declare the workflow's required controls before relying on assurance."
    else:
        status = _reduce_status(findings)
        considered_ids = tuple(
            sorted(
                {
                    evidence_id
                    for finding in findings
                    for evidence_id in finding.evidence_ids
                }
            )
        )

        if status is AssuranceStatus.GREEN:
            reason_codes = (ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,)
            affected_control_ids = ()
            summary = "All required controls have fresh, correlated, current passing evidence."
            next_safe_action = "Continue monitoring the workflow for new runtime evidence."
        else:
            failed_findings = tuple(
                finding for finding in findings if finding.status is not AssuranceStatus.GREEN
            )
            reason_codes = _ordered_reasons(failed_findings)
            affected_control_ids = tuple(
                sorted({finding.control.control_id for finding in failed_findings})
            )
            summary = _customer_summary(status, failed_findings)
            next_safe_action = _next_safe_actions(failed_findings)

    explanation = StateTransitionExplanation(
        previous_status=previous_status,
        current_status=status,
        reason_codes=reason_codes,
        affected_control_ids=affected_control_ids,
        supporting_evidence_ids=considered_ids,
        summary=summary,
        next_safe_action=next_safe_action,
        evaluated_at=evaluated_at,
    )
    return AssuranceEvaluation(
        status=status,
        explanation=explanation,
        considered_evidence_ids=considered_ids,
        ignored_duplicate_evidence_ids=deduplicated.ignored_ids,
    )


def _evaluate_requirement(
    *,
    control: ControlDefinition,
    requirement: RequiredEvidenceSpecification,
    events: Sequence[EvidenceEnvelope],
    collision_keys: frozenset[_DeduplicationKey],
    workflow: WorkflowExecutionReference,
    evaluated_at: datetime,
) -> _Finding:
    matching = tuple(
        event
        for event in events
        if event.control_id == control.control_id
        and event.requirement_id == requirement.requirement_id
        and event.evidence_type is requirement.evidence_type
        and (
            requirement.required_source is None
            or event.source == requirement.required_source
        )
    )
    if not matching:
        return _amber(control, ReasonCode.REQUIRED_EVIDENCE_MISSING)

    collided = tuple(
        event
        for event in matching
        if _deduplication_key(event) in collision_keys
    )
    if collided:
        return _amber(
            control,
            ReasonCode.EVIDENCE_CONFLICT,
            _event_ids(collided),
        )

    correlated = tuple(event for event in matching if event.workflow == workflow)
    if not correlated:
        return _amber(
            control,
            ReasonCode.EVIDENCE_UNCORRELATED,
            _event_ids(matching),
        )

    current = tuple(
        event
        for event in correlated
        if event.provenance == requirement.expected_provenance
    )
    if not current:
        return _amber(
            control,
            ReasonCode.OBSOLETE_PROVENANCE,
            _event_ids(correlated),
        )

    if control.verification_required_after is not None:
        post_remediation = tuple(
            event
            for event in current
            if event.observed_at > control.verification_required_after
        )
        if not post_remediation:
            return _amber(
                control,
                ReasonCode.REMEDIATION_UNVERIFIED,
                _event_ids(current),
            )
        current = post_remediation

    skewed = tuple(
        event
        for event in current
        if event.observed_at - event.ingested_at
        > requirement.freshness.clock_skew_tolerance
        or event.observed_at - evaluated_at
        > requirement.freshness.clock_skew_tolerance
        or event.ingested_at - evaluated_at
        > requirement.freshness.clock_skew_tolerance
    )
    if skewed:
        return _amber(
            control,
            ReasonCode.CLOCK_SKEW_EXCEEDED,
            _event_ids(skewed),
        )

    fresh = tuple(
        event
        for event in current
        if evaluated_at - event.observed_at <= requirement.freshness.max_age
    )
    if not fresh:
        latest = _latest_cohort(current)
        return _amber(control, ReasonCode.EVIDENCE_STALE, _event_ids(latest))

    latest = _latest_cohort(fresh)
    latest_outcomes = {event.outcome for event in latest}
    if len(latest_outcomes) != 1:
        return _amber(
            control,
            ReasonCode.EVIDENCE_CONFLICT,
            _event_ids(latest),
        )

    outcome = next(iter(latest_outcomes))
    if outcome is EvidenceOutcome.FAIL:
        return _Finding(
            control=control,
            status=AssuranceStatus.RED,
            reason=ReasonCode.CONTROL_FAILURE_OBSERVED,
            evidence_ids=_event_ids(latest),
        )
    if outcome is EvidenceOutcome.INCOMPLETE:
        return _amber(
            control,
            ReasonCode.EVIDENCE_INCOMPLETE,
            _event_ids(latest),
        )
    if outcome is EvidenceOutcome.UNAVAILABLE:
        return _amber(
            control,
            ReasonCode.EVIDENCE_UNAVAILABLE,
            _event_ids(latest),
        )
    passing = tuple(
        sorted(
            (event for event in fresh if event.outcome is EvidenceOutcome.PASS),
            key=lambda event: (event.observed_at, event.evidence_id),
            reverse=True,
        )
    )
    if len(passing) < requirement.minimum_count:
        return _amber(
            control,
            ReasonCode.REQUIRED_EVIDENCE_MISSING,
            _event_ids(passing),
        )

    selected = passing[: requirement.minimum_count]
    return _Finding(
        control=control,
        status=AssuranceStatus.GREEN,
        reason=None,
        evidence_ids=_event_ids(selected),
    )


def _deduplicate(events: Sequence[EvidenceEnvelope]) -> _DeduplicatedEvidence:
    groups: dict[_DeduplicationKey, list[EvidenceEnvelope]] = defaultdict(list)
    for event in events:
        groups[_deduplication_key(event)].append(event)

    canonical: list[EvidenceEnvelope] = []
    ignored: list[str] = []
    collision_keys: set[_DeduplicationKey] = set()

    for key in sorted(groups):
        payload_groups: dict[str, list[EvidenceEnvelope]] = defaultdict(list)
        for event in groups[key]:
            payload_groups[_logical_payload(event)].append(event)

        if len(payload_groups) > 1:
            collision_keys.add(key)

        for payload in sorted(payload_groups):
            variants = payload_groups[payload]
            earliest_ingestion = min(event.ingested_at for event in variants)
            earliest_variants = tuple(
                event for event in variants if event.ingested_at == earliest_ingestion
            )
            representative = max(
                earliest_variants,
                key=lambda event: event.evidence_id,
            )
            canonical.append(representative)
            ignored.extend(
                event.evidence_id for event in variants if event is not representative
            )

    return _DeduplicatedEvidence(
        events=tuple(
            sorted(
                canonical,
                key=lambda event: (
                    event.observed_at,
                    event.source,
                    event.source_event_id,
                    event.evidence_id,
                ),
            )
        ),
        ignored_ids=tuple(sorted(ignored)),
        collision_keys=frozenset(collision_keys),
    )


def _logical_payload(event: EvidenceEnvelope) -> str:
    payload = event.model_dump(
        mode="json",
        exclude={"evidence_id", "ingested_at"},
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _deduplication_key(event: EvidenceEnvelope) -> _DeduplicationKey:
    workflow = event.workflow
    return (
        workflow.tenant_id,
        workflow.environment.value,
        workflow.assurance_boundary_id,
        workflow.workflow_id,
        event.source,
        event.source_event_id,
    )


def _latest_cohort(events: Sequence[EvidenceEnvelope]) -> tuple[EvidenceEnvelope, ...]:
    latest_time = max(event.observed_at for event in events)
    return tuple(event for event in events if event.observed_at == latest_time)


def _event_ids(events: Sequence[EvidenceEnvelope]) -> tuple[str, ...]:
    return tuple(sorted({event.evidence_id for event in events}))


def _amber(
    control: ControlDefinition,
    reason: ReasonCode,
    evidence_ids: tuple[str, ...] = (),
) -> _Finding:
    return _Finding(
        control=control,
        status=AssuranceStatus.AMBER,
        reason=reason,
        evidence_ids=evidence_ids,
    )


def _reduce_status(findings: Sequence[_Finding]) -> AssuranceStatus:
    if any(finding.status is AssuranceStatus.RED for finding in findings):
        return AssuranceStatus.RED
    if any(finding.status is AssuranceStatus.AMBER for finding in findings):
        return AssuranceStatus.AMBER
    return AssuranceStatus.GREEN


def _ordered_reasons(findings: Sequence[_Finding]) -> tuple[ReasonCode, ...]:
    return tuple(
        sorted(
            {finding.reason for finding in findings if finding.reason is not None},
            key=_REASON_PRIORITY.__getitem__,
        )
    )


def _customer_summary(
    status: AssuranceStatus,
    findings: Sequence[_Finding],
) -> str:
    details: list[str] = []
    seen: set[tuple[str, ReasonCode]] = set()
    for finding in sorted(
        findings,
        key=lambda item: (
            item.control.control_id,
            _REASON_PRIORITY[item.reason] if item.reason is not None else -1,
        ),
    ):
        if finding.reason is None:
            continue
        key = (finding.control.control_id, finding.reason)
        if key in seen:
            continue
        seen.add(key)
        details.append(
            f"{finding.control.display_name}: {_REASON_TEXT[finding.reason]}"
        )
    return f"Assurance is {status.value}: " + "; ".join(details) + "."


def _next_safe_actions(findings: Sequence[_Finding]) -> str:
    actions: list[str] = []
    for finding in sorted(findings, key=lambda item: item.control.control_id):
        if finding.control.next_safe_action not in actions:
            actions.append(finding.control.next_safe_action)
    return " ".join(actions)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("clock.now() must return a UTC-aware timestamp")
