from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

import pytest
from pydantic import ValidationError

from proofloop.domain.evaluator import evaluate_assurance
from proofloop.domain.models import (
    AssuranceEvaluation,
    AssuranceStatus,
    CanaryResult,
    ControlDefinition,
    Environment,
    EvidenceAttribute,
    EvidenceEnvelope,
    EvidenceFreshnessPolicy,
    EvidenceOutcome,
    EvidenceType,
    IncidentRecord,
    IncidentStatus,
    Provenance,
    ReasonCode,
    RequiredEvidenceSpecification,
    StateTransitionExplanation,
    WorkflowExecutionReference,
)


NOW = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
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
WORKFLOW = WorkflowExecutionReference(
    tenant_id="customer-a",
    environment=Environment.PRODUCTION,
    assurance_boundary_id="customer-a-prod-invoices",
    workflow_id="invoice-processing",
    execution_id="execution-001",
    trace_id="trace-001",
)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def requirement(
    requirement_id: str = "runtime-outcome",
    *,
    minimum_count: int = 1,
    clock_skew_tolerance: timedelta = timedelta(seconds=5),
    provenance: Provenance = CURRENT_PROVENANCE,
) -> RequiredEvidenceSpecification:
    return RequiredEvidenceSpecification(
        requirement_id=requirement_id,
        evidence_type=EvidenceType.CONTROL_OUTCOME,
        freshness=EvidenceFreshnessPolicy(
            max_age=timedelta(minutes=15),
            clock_skew_tolerance=clock_skew_tolerance,
        ),
        expected_provenance=provenance,
        minimum_count=minimum_count,
        required_source="runtime-monitor",
    )


def control(
    control_id: str = "pii-redaction",
    *,
    requirements: tuple[RequiredEvidenceSpecification, ...] | None = None,
    verification_required_after: datetime | None = None,
) -> ControlDefinition:
    return ControlDefinition(
        control_id=control_id,
        display_name=control_id.replace("-", " ").title(),
        required_evidence=requirements or (requirement(),),
        verification_required_after=verification_required_after,
        customer_impact="A required invoice control may not have executed.",
        next_safe_action=f"Inspect {control_id} and run a safe verification canary.",
    )


def evidence(
    *,
    evidence_id: str = "evidence-001",
    requirement_id: str = "runtime-outcome",
    source_event_id: str | None = None,
    control_id: str = "pii-redaction",
    outcome: EvidenceOutcome = EvidenceOutcome.PASS,
    observed_at: datetime = NOW - timedelta(minutes=1),
    ingested_at: datetime | None = None,
    workflow: WorkflowExecutionReference = WORKFLOW,
    provenance: Provenance = CURRENT_PROVENANCE,
    attributes: tuple[EvidenceAttribute, ...] = (),
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
        attributes=attributes,
    )


def evaluate(
    controls: tuple[ControlDefinition, ...],
    events: tuple[EvidenceEnvelope, ...],
    *,
    previous_status: AssuranceStatus | None = None,
) -> AssuranceEvaluation:
    return evaluate_assurance(
        controls=controls,
        evidence=events,
        workflow=WORKFLOW,
        clock=FixedClock(),
        previous_status=previous_status,
    )


def explanation(
    *,
    status: AssuranceStatus,
    reasons: tuple[ReasonCode, ...],
    affected: tuple[str, ...],
) -> StateTransitionExplanation:
    return StateTransitionExplanation(
        current_status=status,
        reason_codes=reasons,
        affected_control_ids=affected,
        summary="Deterministic assurance explanation.",
        next_safe_action="Inspect the affected control.",
        evaluated_at=NOW,
    )


def test_one_requirement_event_cannot_satisfy_another_requirement() -> None:
    result = evaluate(
        (control(requirements=(requirement("approval-check"),)),),
        (evidence(requirement_id="redaction-check"),),
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.REQUIRED_EVIDENCE_MISSING in result.explanation.reason_codes


def test_two_same_type_requirements_need_separately_bound_evidence() -> None:
    selected_control = control(
        "payment-guard",
        requirements=(requirement("redaction-check"), requirement("approval-check")),
    )
    redaction = evidence(
        evidence_id="redaction",
        control_id="payment-guard",
        requirement_id="redaction-check",
    )

    one_result = evaluate((selected_control,), (redaction,))
    two_result = evaluate(
        (selected_control,),
        (
            redaction,
            evidence(
                evidence_id="approval",
                control_id="payment-guard",
                requirement_id="approval-check",
            ),
        ),
    )

    assert one_result.status is AssuranceStatus.AMBER
    assert two_result.status is AssuranceStatus.GREEN


def test_minimum_count_two_with_one_event_is_amber() -> None:
    selected_control = control(requirements=(requirement(minimum_count=2),))

    result = evaluate((selected_control,), (evidence(),))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.REQUIRED_EVIDENCE_MISSING in result.explanation.reason_codes


@pytest.mark.parametrize(
    "workflow_update",
    [
        {"environment": Environment.STAGING},
        {"assurance_boundary_id": "customer-a-staging-invoices"},
    ],
)
def test_environment_or_assurance_boundary_mismatch_is_uncorrelated(
    workflow_update: dict[str, object],
) -> None:
    foreign_workflow = WORKFLOW.model_copy(update=workflow_update)

    result = evaluate((control(),), (evidence(workflow=foreign_workflow),))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_UNCORRELATED in result.explanation.reason_codes


@pytest.mark.parametrize(
    "field_name",
    ["prompt_version", "model_version", "guardrail_version", "tool_catalog_version"],
)
def test_agent_provenance_mismatch_is_obsolete(field_name: str) -> None:
    obsolete = CURRENT_PROVENANCE.model_copy(update={field_name: "obsolete-version"})

    result = evaluate((control(),), (evidence(provenance=obsolete),))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.OBSOLETE_PROVENANCE in result.explanation.reason_codes


def test_deterministic_component_provenance_allows_inapplicable_fields() -> None:
    deterministic = Provenance(
        component_version="approval-service-v1",
        prompt_version=None,
        model_version=None,
        policy_version="approval-policy-v3",
        schema_version="1.0",
        tool_catalog_version=None,
        mcp_server_version=None,
        orchestration_version="approval-flow-v2",
        guardrail_version=None,
        runtime_config_version="approval-config-v4",
    )

    assert deterministic.prompt_version is None
    assert deterministic.guardrail_version is None


def test_partial_provenance_mismatch_cannot_recover() -> None:
    remediation_time = NOW - timedelta(minutes=10)
    mismatched = CURRENT_PROVENANCE.model_copy(
        update={"guardrail_version": "guardrail-v2"}
    )

    result = evaluate(
        (control(verification_required_after=remediation_time),),
        (
            evidence(
                observed_at=remediation_time + timedelta(seconds=1),
                provenance=mismatched,
            ),
        ),
        previous_status=AssuranceStatus.RED,
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.OBSOLETE_PROVENANCE in result.explanation.reason_codes


def test_required_evidence_has_fixed_pass_only_semantics() -> None:
    assert "accepted_outcomes" not in RequiredEvidenceSpecification.model_fields


def test_assurance_evaluation_rejects_status_explanation_mismatch() -> None:
    red_explanation = explanation(
        status=AssuranceStatus.RED,
        reasons=(ReasonCode.CONTROL_FAILURE_OBSERVED,),
        affected=("pii-redaction",),
    )

    with pytest.raises(ValidationError):
        AssuranceEvaluation(
            status=AssuranceStatus.GREEN,
            explanation=red_explanation,
        )


def test_green_explanation_rejects_failure_reason() -> None:
    with pytest.raises(ValidationError):
        explanation(
            status=AssuranceStatus.GREEN,
            reasons=(ReasonCode.CONTROL_FAILURE_OBSERVED,),
            affected=(),
        )


def test_green_explanation_rejects_affected_controls() -> None:
    with pytest.raises(ValidationError):
        explanation(
            status=AssuranceStatus.GREEN,
            reasons=(ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,),
            affected=("pii-redaction",),
        )


def test_non_green_explanation_requires_an_affected_control() -> None:
    with pytest.raises(ValidationError):
        explanation(
            status=AssuranceStatus.AMBER,
            reasons=(ReasonCode.REQUIRED_EVIDENCE_MISSING,),
            affected=(),
        )


def test_resolved_incident_requires_resolution_evidence() -> None:
    with pytest.raises(ValidationError):
        IncidentRecord(
            incident_id="incident-001",
            workflow=WORKFLOW,
            status=IncidentStatus.RESOLVED,
            affected_control_ids=("pii-redaction",),
            opened_at=NOW,
            customer_impact="A required control failed.",
            next_safe_action="Verify remediation before closing the incident.",
        )


def test_passing_canary_requires_confirmed_absence_of_side_effects() -> None:
    with pytest.raises(ValidationError):
        CanaryResult(
            canary_id="pii-canary",
            run_id="run-001",
            workflow=WORKFLOW,
            started_at=NOW,
            completed_at=NOW + timedelta(seconds=1),
            outcome=EvidenceOutcome.PASS,
            evidence_ids=("evidence-001",),
            side_effects_confirmed_absent=False,
        )


def test_small_clock_skew_is_accepted_without_rewriting_timestamps() -> None:
    observed_at = NOW - timedelta(minutes=1)
    ingested_at = observed_at - timedelta(seconds=5)
    event = evidence(observed_at=observed_at, ingested_at=ingested_at)

    result = evaluate((control(),), (event,))

    assert event.observed_at == observed_at
    assert event.ingested_at == ingested_at
    assert result.status is AssuranceStatus.GREEN


def test_excessive_clock_skew_is_amber() -> None:
    observed_at = NOW - timedelta(minutes=1)
    event = evidence(
        observed_at=observed_at,
        ingested_at=observed_at - timedelta(seconds=6),
    )

    result = evaluate((control(),), (event,))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.CLOCK_SKEW_EXCEEDED in result.explanation.reason_codes


@pytest.mark.parametrize(
    "foreign_update",
    [
        {"tenant_id": "customer-b"},
        {"assurance_boundary_id": "customer-a-other-boundary"},
    ],
)
def test_same_source_event_id_in_another_scope_does_not_collide(
    foreign_update: dict[str, object],
) -> None:
    shared_source_event_id = "source-shared"
    target = evidence(
        evidence_id="target",
        source_event_id=shared_source_event_id,
    )
    foreign = evidence(
        evidence_id="foreign",
        source_event_id=shared_source_event_id,
        workflow=WORKFLOW.model_copy(update=foreign_update),
    )

    result = evaluate((control(),), (foreign, target))

    assert result.status is AssuranceStatus.GREEN
    assert result.considered_evidence_ids == ("target",)


def test_conflicting_source_event_reuse_inside_one_boundary_is_amber() -> None:
    passing = evidence(evidence_id="passing", source_event_id="source-collision")
    failing = evidence(
        evidence_id="failing",
        source_event_id="source-collision",
        outcome=EvidenceOutcome.FAIL,
    )

    result = evaluate((control(),), (passing, failing))

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_CONFLICT in result.explanation.reason_codes


def test_evidence_attributes_are_deeply_immutable_and_canonical() -> None:
    event = evidence(
        attributes=(
            EvidenceAttribute(key="zeta", value=2),
            EvidenceAttribute(key="alpha", value="safe"),
        )
    )

    assert tuple(attribute.key for attribute in event.attributes) == ("alpha", "zeta")
    with pytest.raises(ValidationError):
        event.attributes[0].value = "changed"
    with pytest.raises(TypeError):
        mutable_view = cast(Any, event.attributes)
        mutable_view[0] = EvidenceAttribute(key="alpha", value="changed")


def test_simultaneous_red_and_amber_reduces_to_red_and_names_both_controls() -> None:
    result = evaluate(
        (control("audit-logging"), control("pii-redaction")),
        (
            evidence(
                control_id="pii-redaction",
                outcome=EvidenceOutcome.FAIL,
            ),
        ),
    )

    assert result.status is AssuranceStatus.RED
    assert result.explanation.affected_control_ids == (
        "audit-logging",
        "pii-redaction",
    )


def test_future_evidence_beyond_tolerance_is_amber_never_green() -> None:
    result = evaluate(
        (control(),),
        (evidence(observed_at=NOW + timedelta(seconds=6)),),
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.CLOCK_SKEW_EXCEEDED in result.explanation.reason_codes


def test_future_ingestion_timestamp_beyond_tolerance_is_never_green() -> None:
    result = evaluate(
        (control(),),
        (
            evidence(
                observed_at=NOW - timedelta(minutes=1),
                ingested_at=NOW + timedelta(seconds=6),
            ),
        ),
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.CLOCK_SKEW_EXCEEDED in result.explanation.reason_codes


def test_remediation_boundary_equality_remains_amber() -> None:
    remediation_time = NOW - timedelta(minutes=10)

    result = evaluate(
        (control(verification_required_after=remediation_time),),
        (evidence(observed_at=remediation_time),),
        previous_status=AssuranceStatus.RED,
    )

    assert result.status is AssuranceStatus.AMBER
    assert ReasonCode.REMEDIATION_UNVERIFIED in result.explanation.reason_codes


def test_empty_controls_cannot_produce_green() -> None:
    result = evaluate((), ())

    assert result.status is AssuranceStatus.AMBER
    assert result.explanation.reason_codes == (ReasonCode.NO_CONTROLS_DECLARED,)
    assert result.explanation.affected_control_ids == ()


def test_customer_summary_prefers_display_name_and_retains_structured_id() -> None:
    selected_control = control("pii-redaction")

    result = evaluate((selected_control,), ())

    assert selected_control.display_name in result.explanation.summary
    assert result.explanation.affected_control_ids == (selected_control.control_id,)
