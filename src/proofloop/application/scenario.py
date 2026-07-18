"""Seeded, synthetic invoice-control scenario shared by local and AWS demos."""

from __future__ import annotations

from datetime import datetime, timedelta

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


DEMO_PROVENANCE = Provenance(
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


def build_demo_agent(
    *,
    tenant_id: str = "proofloop-demo",
    environment: Environment = Environment.LOCAL,
    assurance_boundary_id: str = "proofloop-demo-local-invoices",
    agent_id: str = "invoice-agent",
) -> AgentDefinition:
    """Build the one synthetic agent used by the scoped vertical slice."""

    scope = AgentScope(
        tenant_id=tenant_id,
        environment=environment,
        assurance_boundary_id=assurance_boundary_id,
        agent_id=agent_id,
    )
    workflow = WorkflowExecutionReference(
        tenant_id=tenant_id,
        environment=environment,
        assurance_boundary_id=assurance_boundary_id,
        workflow_id="invoice-control-assurance",
        execution_id="continuous-assurance",
        trace_id="synthetic-control-monitoring",
    )
    definitions = (
        _control(
            "guardrails",
            "Guardrails active",
            EvidenceType.CANARY_RESULT,
            "safe-canary",
            "A guardrail failure could allow unsafe invoice-agent behavior.",
        ),
        _control(
            "pii-redaction",
            "PII redaction enabled",
            EvidenceType.CONTROL_OUTCOME,
            "runtime-monitor",
            "Unredacted personal data could be exposed.",
        ),
        _control(
            "audit-logging",
            "Audit logging enabled",
            EvidenceType.AUDIT_EVENT,
            "audit-monitor",
            "Reviewers could lose the evidence needed to reconstruct decisions.",
        ),
        _control(
            "hitl",
            "Human-in-the-loop configured",
            EvidenceType.CONTROL_CONFIGURATION,
            "policy-monitor",
            "A consequential invoice decision could bypass required human review.",
        ),
    )
    return AgentDefinition(
        scope=scope,
        workflow=workflow,
        controls=definitions,
        guardrails_control_id="guardrails",
        pii_redaction_control_id="pii-redaction",
        audit_logging_control_id="audit-logging",
        hitl_control_id="hitl",
    )


def seed_fresh_passes(
    service: ProofLoopService,
    agent: AgentDefinition,
    *,
    observed_at: datetime,
    source_suffix: str,
) -> tuple[str, ...]:
    """Emit one metadata-only PASS per declared requirement."""

    evidence_ids: list[str] = []
    for control in agent.controls:
        requirement = control.required_evidence[0]
        evidence_id = f"{control.control_id}-{source_suffix}"
        attributes = [
            EvidenceAttribute(key="control_active", value=True),
            EvidenceAttribute(key="synthetic", value=True),
        ]
        if requirement.evidence_type is EvidenceType.CANARY_RESULT:
            attributes.append(
                EvidenceAttribute(key="side_effects_absent", value=True)
            )
        event = EvidenceEnvelope(
            evidence_id=evidence_id,
            control_id=control.control_id,
            requirement_id=requirement.requirement_id,
            evidence_type=requirement.evidence_type,
            source=requirement.required_source or "runtime-monitor",
            source_event_id=evidence_id,
            workflow=agent.workflow,
            outcome=EvidenceOutcome.PASS,
            observed_at=observed_at,
            ingested_at=observed_at,
            provenance=requirement.expected_provenance,
            attributes=tuple(attributes),
        )
        service.ingest_evidence(agent.scope, event)
        evidence_ids.append(evidence_id)
    return tuple(evidence_ids)


def _control(
    control_id: str,
    display_name: str,
    evidence_type: EvidenceType,
    source: str,
    customer_impact: str,
) -> ControlDefinition:
    return ControlDefinition(
        control_id=control_id,
        display_name=display_name,
        required_evidence=(
            RequiredEvidenceSpecification(
                requirement_id=f"{control_id}-runtime",
                evidence_type=evidence_type,
                freshness=EvidenceFreshnessPolicy(max_age=timedelta(hours=24)),
                expected_provenance=DEMO_PROVENANCE,
                required_source=source,
            ),
        ),
        customer_impact=customer_impact,
        next_safe_action=(
            f"Inspect {display_name.lower()}, remediate it, and emit fresh verified PASS evidence."
        ),
    )
