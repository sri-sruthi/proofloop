from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from proofloop.agents.guardrails import (
    ControlAttribute,
    ControlKey,
    ControlObservation,
    ControlOutcome,
)
from proofloop.agents.workflow import ModelCallStats, PromptBinding
from proofloop.domain.models import EvidenceOutcome, EvidenceType, Environment
from proofloop.infrastructure.agent_integration import (
    AgentIntegrationSettings,
    build_integrated_invoice_agent,
    map_control_observation,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 7, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def settings() -> AgentIntegrationSettings:
    return AgentIntegrationSettings(
        tenant_id="tenant-a",
        environment=Environment.TEST,
        assurance_boundary_id="tenant-a-test-invoices",
        agent_id="invoice-agent",
        workflow_id="integrated-invoice-workflow",
        execution_id="invoice-runtime",
        trace_id="invoice-agent-assurance",
        model_version="fake-model-v0",
    )


def _observation(
    key: ControlKey,
    outcome: ControlOutcome = ControlOutcome.PASS,
) -> ControlObservation:
    attributes = {
        ControlKey.PII_REDACTION: (
            ControlAttribute(key="email_redacted", value=99),
        ),
        ControlKey.AUDIT_LOGGING: (
            ControlAttribute(key="action", value="document-sensitive-action"),
        ),
        ControlKey.HITL_BOUNDARY: (
            ControlAttribute(key="routed_to_human", value=True),
        ),
        ControlKey.EXTRACTION_SCHEMA_VALIDATION: (
            ControlAttribute(key="validated", value=True),
        ),
    }[key]
    return ControlObservation(
        control_key=key,
        outcome=outcome,
        observed_at=OBSERVED_AT,
        component="proofloop.agents.guardrails",
        guardrail_version="invoice-guardrail-v1",
        reason="free text must never cross the bridge",
        safe_next_action="free text must never cross the bridge",
        attributes=attributes,
    )


@pytest.mark.parametrize(
    ("key", "control_id", "requirement_id", "evidence_type", "safe_key"),
    (
        (
            ControlKey.PII_REDACTION,
            "invoice-pii-redaction",
            "invoice-pii-redaction-runtime",
            EvidenceType.CONTROL_EXECUTION,
            "redaction_applied",
        ),
        (
            ControlKey.AUDIT_LOGGING,
            "invoice-audit-logging",
            "invoice-audit-logging-runtime",
            EvidenceType.AUDIT_EVENT,
            "audit_recorded",
        ),
        (
            ControlKey.HITL_BOUNDARY,
            "invoice-hitl-boundary",
            "invoice-hitl-boundary-runtime",
            EvidenceType.CONTROL_OUTCOME,
            "control_active",
        ),
        (
            ControlKey.EXTRACTION_SCHEMA_VALIDATION,
            "invoice-extraction-guardrail",
            "invoice-extraction-schema-runtime",
            EvidenceType.CONTROL_OUTCOME,
            "schema_valid",
        ),
    ),
)
def test_each_observation_maps_to_exactly_one_runtime_requirement(
    settings: AgentIntegrationSettings,
    key: ControlKey,
    control_id: str,
    requirement_id: str,
    evidence_type: EvidenceType,
    safe_key: str,
) -> None:
    agent = build_integrated_invoice_agent(settings)

    evidence = map_control_observation(
        settings=settings,
        agent=agent,
        document_id="doc-opaque-1",
        prompt_binding=PromptBinding(
            prompt_id="invoice.extraction",
            version="1.0.0",
            content_hash="a" * 64,
        ),
        model_stats=ModelCallStats(
            provider_id="fake-model-v0",
            model_calls=1,
            input_tokens=100,
            output_tokens=40,
        ),
        observation=_observation(key),
    )

    assert evidence.control_id == control_id
    assert evidence.requirement_id == requirement_id
    assert evidence.evidence_type is evidence_type
    assert evidence.source == "proofloop.agents.guardrails"
    assert evidence.workflow == agent.workflow
    assert evidence.observed_at == OBSERVED_AT
    assert evidence.outcome is EvidenceOutcome.PASS
    assert len(evidence.attributes) == 1
    assert evidence.attributes[0].key == safe_key
    assert evidence.attributes[0].value is True
    serialized = evidence.model_dump_json()
    assert "free text must never cross" not in serialized
    assert "email_redacted" not in serialized
    assert "99" not in serialized


def test_schema_runtime_and_canary_are_distinct_requirements(
    settings: AgentIntegrationSettings,
) -> None:
    agent = build_integrated_invoice_agent(settings)
    control = next(
        item for item in agent.controls if item.control_id == "invoice-extraction-guardrail"
    )

    assert [(item.requirement_id, item.evidence_type) for item in control.required_evidence] == [
        ("invoice-extraction-schema-runtime", EvidenceType.CONTROL_OUTCOME),
        ("invoice-extraction-safe-canary", EvidenceType.CANARY_RESULT),
    ]


def test_mapping_preserves_full_applicable_provenance_and_outcomes(
    settings: AgentIntegrationSettings,
) -> None:
    agent = build_integrated_invoice_agent(settings)
    evidence = map_control_observation(
        settings=settings,
        agent=agent,
        document_id="doc-opaque-1",
        prompt_binding=PromptBinding(
            prompt_id="invoice.extraction",
            version="1.0.0",
            content_hash="b" * 64,
        ),
        model_stats=ModelCallStats(
            provider_id="fake-model-v0",
            model_calls=1,
            input_tokens=100,
            output_tokens=40,
        ),
        observation=_observation(
            ControlKey.EXTRACTION_SCHEMA_VALIDATION,
            ControlOutcome.UNAVAILABLE,
        ),
    )

    assert evidence.outcome is EvidenceOutcome.UNAVAILABLE
    assert evidence.provenance.component_version == settings.component_version
    assert evidence.provenance.prompt_version == "1.0.0"
    assert evidence.provenance.model_version == "fake-model-v0"
    assert evidence.provenance.policy_version == settings.policy_version
    assert evidence.provenance.schema_version == settings.schema_version
    assert evidence.provenance.tool_catalog_version == settings.tool_catalog_version
    assert evidence.provenance.mcp_server_version is None
    assert evidence.provenance.orchestration_version == settings.orchestration_version
    assert evidence.provenance.guardrail_version == "invoice-guardrail-v1"
    assert evidence.provenance.runtime_config_version == settings.runtime_config_version


def test_source_event_ids_are_distinct_and_deterministic(
    settings: AgentIntegrationSettings,
) -> None:
    agent = build_integrated_invoice_agent(settings)
    binding = PromptBinding(
        prompt_id="invoice.extraction",
        version="1.0.0",
        content_hash="c" * 64,
    )
    stats = ModelCallStats(
        provider_id="fake-model-v0",
        model_calls=1,
        input_tokens=1,
        output_tokens=1,
    )

    first = map_control_observation(
        settings=settings,
        agent=agent,
        document_id="doc-opaque-1",
        prompt_binding=binding,
        model_stats=stats,
        observation=_observation(ControlKey.PII_REDACTION),
    )
    replay = map_control_observation(
        settings=settings,
        agent=agent,
        document_id="doc-opaque-1",
        prompt_binding=binding,
        model_stats=stats,
        observation=_observation(ControlKey.PII_REDACTION),
    )
    other = map_control_observation(
        settings=settings,
        agent=agent,
        document_id="doc-opaque-1",
        prompt_binding=binding,
        model_stats=stats,
        observation=_observation(ControlKey.AUDIT_LOGGING),
    )

    assert first == replay
    assert first.source_event_id != other.source_event_id
    assert len(first.source_event_id) <= 128
    assert len(first.evidence_id) <= 128


def test_domain_and_application_never_import_agent_implementation() -> None:
    repository = Path(__file__).resolve().parents[2]
    for package in ("domain", "application"):
        for path in (repository / "src" / "proofloop" / package).rglob("*.py"):
            assert "proofloop.agents" not in path.read_text(encoding="utf-8"), path
