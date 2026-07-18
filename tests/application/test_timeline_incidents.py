from __future__ import annotations

from datetime import timedelta

from .conftest import ingest_all_passes
from proofloop.domain.models import AssuranceStatus, EvidenceOutcome, IncidentStatus


def test_timeline_is_append_only_status_history_without_repeat_sync_duplicates(system) -> None:
    service, _, clock, agent = system
    ingest_all_passes(service, agent)
    first = service.sync(agent.scope)
    repeated = service.sync(agent.scope)
    clock.advance(timedelta(hours=24, minutes=5))
    amber = service.sync(agent.scope)

    timeline = service.list_timeline(
        agent.scope,
        start=clock.now() - timedelta(days=7),
        end=clock.now(),
    )
    assert first.transition_created is True
    assert repeated.transition_created is False
    assert amber.transition_created is True
    assert [item.current_status for item in timeline] == [
        AssuranceStatus.GREEN,
        AssuranceStatus.AMBER,
    ]
    assert timeline[-1].reason_codes


def test_timeline_query_excludes_entries_older_than_seven_days(system) -> None:
    service, _, clock, agent = system
    service.sync(agent.scope)  # initial missing-evidence AMBER
    clock.advance(timedelta(days=8))

    items = service.list_timeline(
        agent.scope,
        start=clock.now() - timedelta(days=7),
        end=clock.now(),
    )

    assert items == ()


def test_sla_incident_creation_is_idempotent_and_green_resolves_with_evidence(system) -> None:
    service, _, clock, agent = system
    service.sync(agent.scope)  # AMBER starts now
    clock.advance(timedelta(hours=1, minutes=1))

    first = service.sync(agent.scope)
    second = service.sync(agent.scope)
    incidents = service.list_incidents(agent.scope)

    assert first.incident_created is True
    assert second.incident_created is False
    assert len(incidents) == 1
    assert incidents[0].status is IncidentStatus.OPEN
    assert incidents[0].remediation_steps

    ingest_all_passes(service, agent, observed_at=clock.now(), suffix="recovery")
    service.sync(agent.scope)
    resolved = service.list_incidents(agent.scope)
    assert resolved[0].status is IncidentStatus.RESOLVED
    assert resolved[0].resolution_evidence_ids
    assert resolved[0].resolved_at == clock.now()


def test_red_sla_opens_one_red_incident_after_threshold(system) -> None:
    service, _, clock, agent = system
    ingest_all_passes(service, agent)
    clock.advance(timedelta(minutes=1))
    service.record_canary_result(
        agent.scope,
        control_id="guardrails",
        outcome=EvidenceOutcome.FAIL,
        source_event_id="red-sla-failure",
    )
    assert service.sync(agent.scope).incident_created is False

    clock.advance(timedelta(minutes=31))
    first = service.sync(agent.scope)
    repeated = service.sync(agent.scope)
    incidents = service.list_incidents(agent.scope)

    assert first.incident_created is True
    assert repeated.incident_created is False
    assert len(incidents) == 1
    assert incidents[0].assurance_status is AssuranceStatus.RED


def test_open_amber_incident_escalates_in_place_when_state_turns_red(system) -> None:
    service, _, clock, agent = system
    service.sync(agent.scope)
    clock.advance(timedelta(hours=1, minutes=1))
    service.sync(agent.scope)
    original = service.list_incidents(agent.scope)[0]
    assert original.assurance_status is AssuranceStatus.AMBER

    service.record_canary_result(
        agent.scope,
        control_id="guardrails",
        outcome=EvidenceOutcome.FAIL,
        source_event_id="escalated-failure",
    )
    service.sync(agent.scope)
    escalated = service.list_incidents(agent.scope)

    assert len(escalated) == 1
    assert escalated[0].incident_id == original.incident_id
    assert escalated[0].assurance_status is AssuranceStatus.RED
