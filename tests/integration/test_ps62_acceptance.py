from __future__ import annotations

from proofloop.domain.models import AssuranceStatus, IncidentStatus, ReasonCode
from proofloop.infrastructure.demo import run_demo


def test_ps62_success_criterion_1_active_systems_are_green() -> None:
    report = run_demo()
    initial = report.scenes[0]

    assert initial.label == "Fresh runtime proof"
    assert initial.compliance.overall_compliance_status is AssuranceStatus.GREEN
    assert initial.compliance.guardrails_active is True
    assert initial.compliance.pii_redaction_enabled is True
    assert initial.compliance.audit_logging_enabled is True
    assert initial.compliance.hitl_configured is True


def test_ps62_success_criterion_2_failure_is_amber_near_24h_and_red_by_48h() -> None:
    report = run_demo()
    by_label = {scene.label: scene for scene in report.scenes}

    quiet = by_label["No fresh proof at the 24-hour sync"]
    explicit_failure = by_label["Explicit safe canary failure at 48 hours"]
    assert quiet.compliance.overall_compliance_status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_STALE in quiet.compliance.reason_codes
    assert ReasonCode.CONTROL_FAILURE_OBSERVED not in quiet.compliance.reason_codes
    assert explicit_failure.compliance.overall_compliance_status is AssuranceStatus.RED
    assert ReasonCode.CONTROL_FAILURE_OBSERVED in explicit_failure.compliance.reason_codes


def test_ps62_success_criterion_3_timeline_has_ordered_triggered_transitions() -> None:
    report = run_demo()

    assert [item.current_status for item in report.timeline] == [
        AssuranceStatus.GREEN,
        AssuranceStatus.AMBER,
        AssuranceStatus.RED,
        AssuranceStatus.AMBER,
        AssuranceStatus.GREEN,
    ]
    assert tuple(item.evaluated_at for item in report.timeline) == tuple(
        sorted(item.evaluated_at for item in report.timeline)
    )
    assert all(item.reason_codes for item in report.timeline)
    assert len({item.transition_id for item in report.timeline}) == len(report.timeline)


def test_ps62_success_criterion_4_reenable_then_verified_pass_recovers_next_sync() -> None:
    report = run_demo()
    by_label = {scene.label: scene for scene in report.scenes}

    config_only = by_label["Guardrail re-enabled; verification still required"]
    recovered = by_label["Fresh post-remediation proof"]
    assert config_only.compliance.overall_compliance_status is AssuranceStatus.AMBER
    assert ReasonCode.REMEDIATION_UNVERIFIED in config_only.compliance.reason_codes
    assert recovered.compliance.overall_compliance_status is AssuranceStatus.GREEN
    assert recovered.compliance.evaluated_at > config_only.compliance.evaluated_at
    assert report.incidents[0].status is IncidentStatus.RESOLVED
    assert report.incidents[0].resolution_evidence_ids


def test_demo_is_deterministic_across_repeated_runs() -> None:
    first = run_demo()
    second = run_demo()

    assert first == second
