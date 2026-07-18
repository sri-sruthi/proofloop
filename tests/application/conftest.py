from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from proofloop.application.models import AgentDefinition, AgentScope, IncidentSlaPolicy
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
    prompt_version=None,
    model_version=None,
    policy_version="invoice-policy-v1",
    schema_version="1.0",
    tool_catalog_version=None,
    mcp_server_version=None,
    orchestration_version="invoice-flow-v1",
    guardrail_version="invoice-guardrail-v1",
    runtime_config_version="invoice-runtime-v1",
)


def make_scope(
    *,
    tenant_id: str = "tenant-a",
    environment: Environment = Environment.TEST,
    assurance_boundary_id: str = "tenant-a-test-invoices",
    agent_id: str = "invoice-agent",
) -> AgentScope:
    return AgentScope(
        tenant_id=tenant_id,
        environment=environment,
        assurance_boundary_id=assurance_boundary_id,
        agent_id=agent_id,
    )


def make_workflow(scope: AgentScope) -> WorkflowExecutionReference:
    return WorkflowExecutionReference(
        tenant_id=scope.tenant_id,
        environment=scope.environment,
        assurance_boundary_id=scope.assurance_boundary_id,
        workflow_id="invoice-workflow",
        execution_id=f"{scope.agent_id}-execution",
        trace_id=f"{scope.agent_id}-trace",
    )


def make_control(
    control_id: str,
    *,
    evidence_type: EvidenceType = EvidenceType.CONTROL_OUTCOME,
    source: str = "runtime-monitor",
    verification_required_after: datetime | None = None,
) -> ControlDefinition:
    return ControlDefinition(
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
        verification_required_after=verification_required_after,
        customer_impact=f"The {control_id} safety obligation may not be enforced.",
        next_safe_action=f"Inspect {control_id} and emit fresh verified PASS evidence.",
    )


def make_agent(scope: AgentScope | None = None) -> AgentDefinition:
    selected_scope = scope or make_scope()
    return AgentDefinition(
        scope=selected_scope,
        workflow=make_workflow(selected_scope),
        controls=(
            make_control(
                "guardrails",
                evidence_type=EvidenceType.CANARY_RESULT,
                source="safe-canary",
            ),
            make_control("pii-redaction"),
            make_control("audit-logging"),
            make_control("hitl"),
        ),
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
    outcome: EvidenceOutcome = EvidenceOutcome.PASS,
    observed_at: datetime = START,
    workflow: WorkflowExecutionReference | None = None,
    attributes: tuple[EvidenceAttribute, ...] | None = None,
) -> EvidenceEnvelope:
    control = next(item for item in agent.controls if item.control_id == control_id)
    requirement = control.required_evidence[0]
    event_id = evidence_id or f"{control_id}-{outcome.value.lower()}"
    selected_attributes = attributes
    if selected_attributes is None:
        selected_attributes = (
            (
                EvidenceAttribute(key="side_effects_absent", value=True),
                EvidenceAttribute(key="synthetic", value=True),
            )
            if requirement.evidence_type is EvidenceType.CANARY_RESULT
            else ()
        )
    return EvidenceEnvelope(
        evidence_id=event_id,
        control_id=control_id,
        requirement_id=requirement.requirement_id,
        evidence_type=requirement.evidence_type,
        source=requirement.required_source or "runtime-monitor",
        source_event_id=source_event_id or event_id,
        workflow=workflow or agent.workflow,
        outcome=outcome,
        observed_at=observed_at,
        ingested_at=observed_at,
        provenance=requirement.expected_provenance,
        attributes=selected_attributes,
    )


def ingest_all_passes(
    service: ProofLoopService,
    agent: AgentDefinition,
    *,
    observed_at: datetime = START,
    suffix: str = "initial",
) -> None:
    for control in agent.controls:
        service.ingest_evidence(
            agent.scope,
            make_evidence(
                agent,
                control.control_id,
                evidence_id=f"{control.control_id}-{suffix}",
                source_event_id=f"{control.control_id}-{suffix}",
                observed_at=observed_at,
            ),
        )


@pytest.fixture
def system() -> tuple[ProofLoopService, InMemoryProofLoopStore, VirtualClock, AgentDefinition]:
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
        incident_sla=IncidentSlaPolicy(
            amber_after=timedelta(hours=1),
            red_after=timedelta(minutes=30),
        ),
    )
    agent = make_agent()
    service.register_agent(agent)
    return service, store, clock, agent
