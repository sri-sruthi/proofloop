from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from proofloop.application.models import AgentDefinition, AgentScope
from proofloop.application.service import ProofLoopService
from proofloop.domain.models import (
    ControlDefinition,
    Environment,
    EvidenceAttribute,
    EvidenceEnvelope,
    EvidenceFreshnessPolicy,
    EvidenceOutcome,
    EvidenceType,
    Provenance,
    RequiredEvidenceSpecification,
    WorkflowExecutionReference,
)
from proofloop.infrastructure.memory import InMemoryProofLoopStore, VirtualClock


START = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
PROVENANCE = Provenance(
    component_version="invoice-assurance-v1",
    policy_version="invoice-policy-v1",
    schema_version="1.0",
    orchestration_version="invoice-flow-v1",
    guardrail_version="invoice-guardrail-v1",
    runtime_config_version="invoice-runtime-v1",
)


def make_agent() -> AgentDefinition:
    scope = AgentScope(
        tenant_id="tenant-a",
        environment=Environment.TEST,
        assurance_boundary_id="tenant-a-test-invoices",
        agent_id="invoice-agent",
    )
    workflow = WorkflowExecutionReference(
        tenant_id=scope.tenant_id,
        environment=scope.environment,
        assurance_boundary_id=scope.assurance_boundary_id,
        workflow_id="invoice-workflow",
        execution_id="invoice-agent-execution",
        trace_id="invoice-agent-trace",
    )
    controls = []
    for control_id, evidence_type, source in (
        ("guardrails", EvidenceType.CANARY_RESULT, "safe-canary"),
        ("pii-redaction", EvidenceType.CONTROL_OUTCOME, "runtime-monitor"),
        ("audit-logging", EvidenceType.CONTROL_OUTCOME, "runtime-monitor"),
        ("hitl", EvidenceType.CONTROL_OUTCOME, "runtime-monitor"),
    ):
        controls.append(
            ControlDefinition(
                control_id=control_id,
                display_name=control_id.replace("-", " ").title(),
                required_evidence=(
                    RequiredEvidenceSpecification(
                        requirement_id=f"{control_id}-runtime",
                        evidence_type=evidence_type,
                        freshness=EvidenceFreshnessPolicy(max_age=timedelta(hours=24)),
                        expected_provenance=PROVENANCE,
                        required_source=source,
                    ),
                ),
                customer_impact=f"The {control_id} safety obligation may not be enforced.",
                next_safe_action=f"Inspect {control_id} and emit fresh verified PASS evidence.",
            )
        )
    return AgentDefinition(
        scope=scope,
        workflow=workflow,
        controls=tuple(controls),
        guardrails_control_id="guardrails",
        pii_redaction_control_id="pii-redaction",
        audit_logging_control_id="audit-logging",
        hitl_control_id="hitl",
    )


def make_evidence(
    agent: AgentDefinition,
    control_id: str,
    *,
    evidence_id: str | None = None,
    source_event_id: str | None = None,
) -> EvidenceEnvelope:
    control = next(item for item in agent.controls if item.control_id == control_id)
    requirement = control.required_evidence[0]
    selected_id = evidence_id or f"{control_id}-pass"
    return EvidenceEnvelope(
        evidence_id=selected_id,
        control_id=control_id,
        requirement_id=requirement.requirement_id,
        evidence_type=requirement.evidence_type,
        source=requirement.required_source or "runtime-monitor",
        source_event_id=source_event_id or selected_id,
        workflow=agent.workflow,
        outcome=EvidenceOutcome.PASS,
        observed_at=START,
        ingested_at=START,
        provenance=requirement.expected_provenance,
        attributes=(
            (
                EvidenceAttribute(key="synthetic", value=True),
                EvidenceAttribute(key="side_effects_absent", value=True),
            )
            if requirement.evidence_type is EvidenceType.CANARY_RESULT
            else ()
        ),
    )


def ingest_all_passes(service: ProofLoopService, agent: AgentDefinition) -> None:
    for control in agent.controls:
        service.ingest_evidence(agent.scope, make_evidence(agent, control.control_id))


@pytest.fixture
def system():
    store = InMemoryProofLoopStore()
    clock = VirtualClock(START)
    service = ProofLoopService(
        agents=store,
        evidence=store,
        compliance=store,
        timeline=store,
        incidents=store,
        state=store,
        clock=clock,
    )
    agent = make_agent()
    service.register_agent(agent)
    return service, store, clock, agent
