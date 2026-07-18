from __future__ import annotations

from datetime import datetime, timedelta, timezone

from proofloop.application.models import (
    AgentDefinition,
    AgentScope,
    ComplianceIncident,
    ComplianceReadModel,
    ControlCompliance,
    TimelineEntry,
)
from proofloop.domain.models import (
    AssuranceStatus,
    ControlDefinition,
    Environment,
    EvidenceAttribute,
    EvidenceEnvelope,
    EvidenceFreshnessPolicy,
    EvidenceOutcome,
    EvidenceType,
    IncidentStatus,
    Provenance,
    ReasonCode,
    RequiredEvidenceSpecification,
    WorkflowExecutionReference,
)


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
    control = next(value for value in agent.controls if value.control_id == control_id)
    requirement = control.required_evidence[0]
    selected_id = evidence_id or f"{control_id}-pass"
    attributes = (
        (
            EvidenceAttribute(key="side_effects_absent", value=True),
            EvidenceAttribute(key="synthetic", value=True),
        )
        if requirement.evidence_type is EvidenceType.CANARY_RESULT
        else ()
    )
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
        attributes=attributes,
    )


def build_compliance(agent: AgentDefinition) -> ComplianceReadModel:
    controls = tuple(
        ControlCompliance(
            control_id=control.control_id,
            display_name=control.display_name,
            status=AssuranceStatus.GREEN,
            active=True,
            last_evidence_at=START,
            reason_codes=(ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,),
            evidence_ids=(f"{control.control_id}-pass",),
        )
        for control in agent.controls
    )
    return ComplianceReadModel(
        agent_id=agent.scope.agent_id,
        tenant_id=agent.scope.tenant_id,
        environment=agent.scope.environment,
        assurance_boundary_id=agent.scope.assurance_boundary_id,
        guardrails_active=True,
        last_violation_timestamp=None,
        pii_redaction_enabled=True,
        audit_logging_enabled=True,
        hitl_configured=True,
        overall_compliance_status=AssuranceStatus.GREEN,
        reason_codes=(ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,),
        supporting_evidence_ids=tuple(
            f"{control.control_id}-pass" for control in agent.controls
        ),
        evaluated_at=START,
        next_safe_action="Continue monitoring.",
        controls=controls,
    )


def build_timeline(agent: AgentDefinition) -> TimelineEntry:
    return TimelineEntry(
        transition_id="transition-green",
        scope=agent.scope,
        previous_status=None,
        current_status=AssuranceStatus.GREEN,
        reason_codes=(ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,),
        summary="All required evidence is verified.",
        next_safe_action="Continue monitoring.",
        evaluated_at=START,
        expires_at=START + timedelta(days=7),
    )


def build_incident(agent: AgentDefinition) -> ComplianceIncident:
    return ComplianceIncident(
        incident_id="incident-amber",
        scope=agent.scope,
        workflow=agent.workflow,
        status=IncidentStatus.OPEN,
        assurance_status=AssuranceStatus.AMBER,
        affected_control_ids=("guardrails",),
        opened_at=START,
        customer_impact="Guardrail assurance is unavailable.",
        remediation_steps="Run a safe canary and verify fresh evidence.",
    )
