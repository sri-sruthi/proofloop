from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import product

import pytest

from proofloop.domain.evaluator import evaluate_assurance
from proofloop.domain.models import (
    AssuranceStatus,
    ControlDefinition,
    Environment,
    EvidenceEnvelope,
    EvidenceFreshnessPolicy,
    EvidenceOutcome,
    EvidenceType,
    Provenance,
    ReasonCode,
    RequiredEvidenceSpecification,
    WorkflowExecutionReference,
)


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
CURRENT_PROVENANCE = Provenance(
    component_version="extraction-agent-v2",
    prompt_version="prompt-v2",
    model_version="model-v3",
    policy_version="policy-v4",
    schema_version="1.0",
    tool_catalog_version="tools-v2",
    mcp_server_version="mcp-v1",
    orchestration_version="orchestrator-v2",
    guardrail_version="guardrail-v3",
    runtime_config_version="runtime-v5",
)
OBSOLETE_PROVENANCE = Provenance(
    component_version="extraction-agent-v1",
    prompt_version="prompt-v1",
    model_version="model-v3",
    policy_version="policy-v3",
    schema_version="1.0",
    tool_catalog_version="tools-v1",
    mcp_server_version="mcp-v1",
    orchestration_version="orchestrator-v1",
    guardrail_version="guardrail-v2",
    runtime_config_version="runtime-v4",
)
WORKFLOW = WorkflowExecutionReference(
    tenant_id="customer-a",
    environment=Environment.PRODUCTION,
    assurance_boundary_id="customer-a-prod-invoices",
    workflow_id="invoice-processing",
    execution_id="execution-001",
    trace_id="trace-001",
)


class FixedClock:
    def __init__(self, value: datetime = NOW) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value


def required_evidence() -> RequiredEvidenceSpecification:
    return RequiredEvidenceSpecification(
        requirement_id="runtime-outcome",
        evidence_type=EvidenceType.CONTROL_OUTCOME,
        freshness=EvidenceFreshnessPolicy(max_age=timedelta(minutes=15)),
        expected_provenance=CURRENT_PROVENANCE,
        minimum_count=1,
        required_source="runtime-monitor",
    )


def control(
    control_id: str = "pii-redaction",
    *,
    verification_required_after: datetime | None = None,
) -> ControlDefinition:
    return ControlDefinition(
        control_id=control_id,
        display_name=control_id.replace("-", " ").title(),
        required_evidence=(required_evidence(),),
        verification_required_after=verification_required_after,
        customer_impact="Unredacted customer data could be exposed.",
        next_safe_action=f"Inspect {control_id} and run a safe verification canary.",
    )


def evidence(
    *,
    evidence_id: str = "evidence-001",
    source_event_id: str | None = None,
    control_id: str = "pii-redaction",
    requirement_id: str = "runtime-outcome",
    outcome: EvidenceOutcome = EvidenceOutcome.PASS,
    observed_at: datetime = NOW - timedelta(minutes=1),
    ingested_at: datetime | None = None,
    workflow: WorkflowExecutionReference = WORKFLOW,
    provenance: Provenance = CURRENT_PROVENANCE,
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        evidence_id=evidence_id,
        control_id=control_id,
        requirement_id=requirement_id,
        evidence_type=EvidenceType.CONTROL_OUTCOME,
        source="runtime-monitor",
        source_event_id=source_event_id or evidence_id,
        workflow=workflow,
        outcome=outcome,
        observed_at=observed_at,
        ingested_at=ingested_at or observed_at + timedelta(seconds=2),
        provenance=provenance,
    )


def evaluate(
    controls: tuple[ControlDefinition, ...],
    events: tuple[EvidenceEnvelope, ...],
    *,
    previous_status: AssuranceStatus | None = None,
):
    return evaluate_assurance(
        controls=controls,
        evidence=events,
        workflow=WORKFLOW,
        clock=FixedClock(),
        previous_status=previous_status,
    )


def test_complete_passing_evidence_is_green() -> None:
    controls = (control("pii-redaction"), control("audit-logging"))
    events = (
        evidence(control_id="pii-redaction", evidence_id="pii-pass"),
        evidence(control_id="audit-logging", evidence_id="audit-pass"),
    )

    result = evaluate(controls, events)

    assert result.status is AssuranceStatus.GREEN
    assert result.explanation.reason_codes == (ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,)


def test_missing_required_evidence_is_amber() -> None:
    result = evaluate((control(),), ())

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.REQUIRED_EVIDENCE_MISSING in result.explanation.reason_codes


def test_stale_evidence_is_amber() -> None:
    stale = evidence(observed_at=NOW - timedelta(minutes=16))

    result = evaluate((control(),), (stale,))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_STALE in result.explanation.reason_codes


def test_conflicting_latest_evidence_is_amber() -> None:
    observed_at = NOW - timedelta(minutes=1)
    passing = evidence(evidence_id="passing", observed_at=observed_at)
    failing = evidence(
        evidence_id="failing",
        outcome=EvidenceOutcome.FAIL,
        observed_at=observed_at,
    )

    result = evaluate((control(),), (passing, failing))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_CONFLICT in result.explanation.reason_codes


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        (EvidenceOutcome.INCOMPLETE, ReasonCode.EVIDENCE_INCOMPLETE),
        (EvidenceOutcome.UNAVAILABLE, ReasonCode.EVIDENCE_UNAVAILABLE),
    ],
)
def test_non_decisive_outcome_is_amber(
    outcome: EvidenceOutcome,
    reason: ReasonCode,
) -> None:
    result = evaluate((control(),), (evidence(outcome=outcome),))

    assert result.status is AssuranceStatus.AMBER
    assert reason in result.explanation.reason_codes


def test_explicit_failed_outcome_is_red() -> None:
    result = evaluate((control(),), (evidence(outcome=EvidenceOutcome.FAIL),))

    assert result.status is AssuranceStatus.RED
    assert ReasonCode.CONTROL_FAILURE_OBSERVED in result.explanation.reason_codes


def test_wrong_workflow_execution_cannot_satisfy_a_control() -> None:
    other_workflow = WORKFLOW.model_copy(update={"execution_id": "execution-002"})

    result = evaluate((control(),), (evidence(workflow=other_workflow),))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_UNCORRELATED in result.explanation.reason_codes


def test_obsolete_prompt_or_policy_provenance_cannot_establish_recovery() -> None:
    remediation_time = NOW - timedelta(minutes=10)
    obsolete = evidence(
        observed_at=NOW - timedelta(minutes=1),
        provenance=OBSOLETE_PROVENANCE,
    )

    result = evaluate(
        (control(verification_required_after=remediation_time),),
        (obsolete,),
        previous_status=AssuranceStatus.RED,
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.OBSOLETE_PROVENANCE in result.explanation.reason_codes


def test_configuration_change_without_fresh_evidence_cannot_recover() -> None:
    remediation_time = NOW - timedelta(minutes=10)
    before_change = evidence(observed_at=remediation_time - timedelta(seconds=1))

    result = evaluate(
        (control(verification_required_after=remediation_time),),
        (before_change,),
        previous_status=AssuranceStatus.RED,
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.REMEDIATION_UNVERIFIED in result.explanation.reason_codes


def test_fresh_post_remediation_evidence_can_recover() -> None:
    remediation_time = NOW - timedelta(minutes=10)
    after_change = evidence(observed_at=remediation_time + timedelta(seconds=1))

    result = evaluate(
        (control(verification_required_after=remediation_time),),
        (after_change,),
        previous_status=AssuranceStatus.RED,
    )

    assert result.status is AssuranceStatus.GREEN
    assert result.explanation.previous_status is AssuranceStatus.RED


def test_duplicate_source_event_does_not_alter_the_result() -> None:
    original = evidence(evidence_id="original", source_event_id="source-001")
    duplicate = evidence(evidence_id="duplicate", source_event_id="source-001")

    one_result = evaluate((control(),), (original,))
    duplicate_result = evaluate((control(),), (duplicate, original))

    assert duplicate_result.status is one_result.status
    assert duplicate_result.explanation.reason_codes == one_result.explanation.reason_codes
    assert duplicate_result.considered_evidence_ids == ("original",)


def test_out_of_order_delivery_uses_event_time_not_input_order() -> None:
    older_failure = evidence(
        evidence_id="older-failure",
        outcome=EvidenceOutcome.FAIL,
        observed_at=NOW - timedelta(minutes=5),
        ingested_at=NOW - timedelta(seconds=5),
    )
    newer_pass = evidence(
        evidence_id="newer-pass",
        outcome=EvidenceOutcome.PASS,
        observed_at=NOW - timedelta(minutes=1),
        ingested_at=NOW - timedelta(seconds=30),
    )

    result = evaluate((control(),), (newer_pass, older_failure))

    assert result.status is AssuranceStatus.GREEN
    assert result.considered_evidence_ids == ("newer-pass",)


def test_single_requirement_state_matrix_never_produces_unsupported_green() -> None:
    for present, fresh, correlated, current, outcome in product(
        (False, True),
        (False, True),
        (False, True),
        (False, True),
        tuple(EvidenceOutcome),
    ):
        events: tuple[EvidenceEnvelope, ...] = ()
        if present:
            target_workflow = (
                WORKFLOW
                if correlated
                else WORKFLOW.model_copy(update={"execution_id": "wrong-execution"})
            )
            events = (
                evidence(
                    outcome=outcome,
                    observed_at=(
                        NOW - timedelta(minutes=1)
                        if fresh
                        else NOW - timedelta(minutes=16)
                    ),
                    workflow=target_workflow,
                    provenance=CURRENT_PROVENANCE if current else OBSOLETE_PROVENANCE,
                ),
            )

        result = evaluate((control(),), events)
        supported = (
            present
            and fresh
            and correlated
            and current
            and outcome is EvidenceOutcome.PASS
        )
        assert (result.status is AssuranceStatus.GREEN) is supported


@pytest.mark.parametrize(
    ("events", "expected_status", "control_id"),
    [
        ((), AssuranceStatus.AMBER, "pii-redaction"),
        (
            (evidence(control_id="audit-logging", outcome=EvidenceOutcome.FAIL),),
            AssuranceStatus.RED,
            "audit-logging",
        ),
    ],
)
def test_customer_explanation_names_control_and_next_safe_action(
    events: tuple[EvidenceEnvelope, ...],
    expected_status: AssuranceStatus,
    control_id: str,
) -> None:
    selected_control = control(control_id)

    result = evaluate((selected_control,), events)

    assert result.status is expected_status
    assert control_id in result.explanation.affected_control_ids
    assert selected_control.display_name in result.explanation.summary
    assert selected_control.next_safe_action in result.explanation.next_safe_action


def test_two_same_type_requirements_need_separately_bound_evidence() -> None:
    first_requirement = required_evidence().model_copy(
        update={"requirement_id": "redaction-check"}
    )
    second_requirement = required_evidence().model_copy(
        update={"requirement_id": "approval-check"}
    )
    multi_requirement_control = control("payment-guard").model_copy(
        update={"required_evidence": (first_requirement, second_requirement)}
    )

    result = evaluate(
        (multi_requirement_control,),
        (
            evidence(
                control_id="payment-guard",
                requirement_id="redaction-check",
                evidence_id="only-one",
            ),
        ),
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.REQUIRED_EVIDENCE_MISSING in result.explanation.reason_codes
