from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

import proofloop.domain.models as models


UTC_NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


def provenance() -> models.Provenance:
    return models.Provenance(
        component_version="redactor-v2",
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


def workflow() -> models.WorkflowExecutionReference:
    return models.WorkflowExecutionReference(
        tenant_id="customer-a",
        environment=models.Environment.PRODUCTION,
        assurance_boundary_id="customer-a-prod-invoices",
        workflow_id="invoice-processing",
        execution_id="execution-001",
        trace_id="trace-001",
    )


def test_evidence_outcome_pass_serialized_contract_is_stable() -> None:
    assert models.EvidenceOutcome.PASS.value == "PASS"


def test_contracts_forbid_unknown_fields_and_are_immutable() -> None:
    value = models.Provenance(
        component_version="redactor-v2",
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

    with pytest.raises(ValidationError):
        models.Provenance.model_validate(
            {
                **value.model_dump(),
                "aws_region": "us-east-1",
            }
        )

    with pytest.raises(ValidationError):
        value.policy_version = "policy-v5"


def test_freshness_policy_requires_a_positive_window() -> None:
    with pytest.raises(ValidationError):
        models.EvidenceFreshnessPolicy(max_age=timedelta(0))


@pytest.mark.parametrize(
    "field_name",
    ["observed_at", "ingested_at"],
)
def test_evidence_timestamps_must_be_utc_aware(field_name: str) -> None:
    values = {
        "evidence_id": "evidence-001",
        "control_id": "pii-redaction",
        "requirement_id": "runtime-outcome",
        "evidence_type": models.EvidenceType.CONTROL_OUTCOME,
        "source": "local-redactor",
        "source_event_id": "source-event-001",
        "workflow": workflow(),
        "outcome": models.EvidenceOutcome.PASS,
        "observed_at": UTC_NOW,
        "ingested_at": UTC_NOW,
        "provenance": provenance(),
    }
    values[field_name] = datetime(2026, 7, 17, 12, 0)

    with pytest.raises(ValidationError):
        models.EvidenceEnvelope.model_validate(values)


def test_canary_definition_rejects_real_customer_side_effects() -> None:
    with pytest.raises(ValidationError):
        models.CanaryDefinition.model_validate(
            {
                "canary_id": "pii-canary",
                "control_id": "pii-redaction",
                "display_name": "Reserved PII redaction probe",
                "evidence_type": models.EvidenceType.CANARY_RESULT,
                "expected_outcome": models.EvidenceOutcome.PASS,
                "safety_mode": "PRODUCTION",
                "next_safe_action": (
                    "Investigate the redaction path without mutating customer data."
                ),
            }
        )


def test_canary_result_requires_completion_after_start() -> None:
    with pytest.raises(ValidationError):
        models.CanaryResult(
            canary_id="pii-canary",
            run_id="run-001",
            workflow=workflow(),
            started_at=UTC_NOW,
            completed_at=UTC_NOW - timedelta(seconds=1),
            outcome=models.EvidenceOutcome.PASS,
            evidence_ids=("evidence-001",),
            side_effects_confirmed_absent=True,
        )
