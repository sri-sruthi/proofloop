from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from .conftest import START, ingest_all_passes
from proofloop.application.errors import ApplicationError, ErrorCode
from proofloop.domain.models import AssuranceStatus, EvidenceOutcome, ReasonCode


def test_fresh_healthy_evidence_populates_ps62_read_model(system) -> None:
    service, _, _, agent = system
    ingest_all_passes(service, agent)

    result = service.sync(agent.scope).compliance

    assert result.guardrails_active is True
    assert result.pii_redaction_enabled is True
    assert result.audit_logging_enabled is True
    assert result.hitl_configured is True
    assert result.overall_compliance_status is AssuranceStatus.GREEN
    assert result.tenant_id == agent.scope.tenant_id
    assert result.environment == agent.scope.environment
    assert result.assurance_boundary_id == agent.scope.assurance_boundary_id
    assert len(result.supporting_evidence_ids) == 4
    assert result.reason_codes == (ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED,)


def test_quiet_evidence_after_24_hours_is_amber_never_red(system) -> None:
    service, _, clock, agent = system
    ingest_all_passes(service, agent)
    assert service.sync(agent.scope).compliance.overall_compliance_status is AssuranceStatus.GREEN

    clock.advance(timedelta(hours=24, minutes=5))
    result = service.sync(agent.scope).compliance

    assert result.overall_compliance_status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_STALE in result.reason_codes
    assert result.guardrails_active is None


def test_explicit_safe_canary_failure_at_48_hours_is_red(system) -> None:
    service, _, clock, agent = system
    ingest_all_passes(service, agent)
    service.sync(agent.scope)
    clock.advance(timedelta(hours=48))

    service.record_canary_result(
        agent.scope,
        control_id="guardrails",
        outcome=EvidenceOutcome.FAIL,
        source_event_id="48h-safe-canary",
    )
    result = service.sync(agent.scope).compliance

    assert result.overall_compliance_status is AssuranceStatus.RED
    assert result.guardrails_active is False
    assert result.last_violation_timestamp == clock.now()
    assert ReasonCode.CONTROL_FAILURE_OBSERVED in result.reason_codes


def test_remediation_alone_stays_amber_until_fresh_pass(system) -> None:
    service, _, clock, agent = system
    ingest_all_passes(service, agent)
    service.sync(agent.scope)
    clock.advance(timedelta(hours=48))
    service.record_canary_result(
        agent.scope,
        control_id="guardrails",
        outcome=EvidenceOutcome.FAIL,
        source_event_id="canary-fail",
    )
    assert service.sync(agent.scope).compliance.overall_compliance_status is AssuranceStatus.RED

    service.mark_remediated(agent.scope, control_ids=("guardrails",))
    after_config = service.sync(agent.scope).compliance
    assert after_config.overall_compliance_status is AssuranceStatus.AMBER
    assert ReasonCode.REMEDIATION_UNVERIFIED in after_config.reason_codes

    clock.advance(timedelta(minutes=5))
    ingest_all_passes(service, agent, observed_at=clock.now(), suffix="verified")
    recovered = service.sync(agent.scope).compliance
    assert recovered.overall_compliance_status is AssuranceStatus.GREEN
    assert recovered.guardrails_active is True
    assert recovered.last_violation_timestamp == START + timedelta(hours=48)


def test_remediation_timestamp_must_be_utc_aware(system) -> None:
    service, _, _, agent = system

    with pytest.raises(ApplicationError) as captured:
        service.mark_remediated(
            agent.scope,
            control_ids=("guardrails",),
            at=datetime(2026, 7, 18, 9, 0),
        )

    assert captured.value.code is ErrorCode.INVALID_REQUEST
