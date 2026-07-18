"""Deterministic seconds-long PS-6.2 demonstration composition."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from proofloop.application.models import (
    ApplicationModel,
    ComplianceIncident,
    ComplianceReadModel,
    IncidentSlaPolicy,
    TimelineEntry,
)
from proofloop.application.scenario import build_demo_agent, seed_fresh_passes
from proofloop.application.service import ProofLoopService
from proofloop.domain.models import EvidenceOutcome
from proofloop.infrastructure.memory import InMemoryProofLoopStore, VirtualClock


DEMO_START = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)


class DemoScene(ApplicationModel):
    label: str
    compliance: ComplianceReadModel


class DemoReport(ApplicationModel):
    scenes: tuple[DemoScene, ...]
    timeline: tuple[TimelineEntry, ...]
    incidents: tuple[ComplianceIncident, ...]


def run_demo() -> DemoReport:
    """Run the complete failure-and-recovery story without wall-clock waiting."""

    store = InMemoryProofLoopStore()
    clock = VirtualClock(DEMO_START)
    service = ProofLoopService(
        agents=store,
        evidence=store,
        compliance=store,
        timeline=store,
        incidents=store,
        state=store,
        clock=clock,
        incident_sla=IncidentSlaPolicy(
            amber_after=timedelta(minutes=30),
            red_after=timedelta(minutes=15),
        ),
    )
    agent = build_demo_agent()
    service.register_agent(agent)
    seed_fresh_passes(
        service,
        agent,
        observed_at=clock.now(),
        source_suffix="initial",
    )
    scenes = [
        DemoScene(
            label="Fresh runtime proof",
            compliance=service.sync(agent.scope).compliance,
        )
    ]

    clock.advance(timedelta(hours=24, minutes=5))
    scenes.append(
        DemoScene(
            label="No fresh proof at the 24-hour sync",
            compliance=service.sync(agent.scope).compliance,
        )
    )

    clock.advance(timedelta(minutes=31))
    service.sync(agent.scope)

    clock.set(DEMO_START + timedelta(hours=48))
    service.record_canary_result(
        agent.scope,
        control_id="guardrails",
        outcome=EvidenceOutcome.FAIL,
        source_event_id="48h-safe-canary-failure",
    )
    scenes.append(
        DemoScene(
            label="Explicit safe canary failure at 48 hours",
            compliance=service.sync(agent.scope).compliance,
        )
    )

    service.mark_remediated(agent.scope, control_ids=("guardrails",))
    scenes.append(
        DemoScene(
            label="Guardrail re-enabled; verification still required",
            compliance=service.sync(agent.scope).compliance,
        )
    )

    clock.advance(timedelta(minutes=5))
    seed_fresh_passes(
        service,
        agent,
        observed_at=clock.now(),
        source_suffix="post-remediation",
    )
    scenes.append(
        DemoScene(
            label="Fresh post-remediation proof",
            compliance=service.sync(agent.scope).compliance,
        )
    )

    return DemoReport(
        scenes=tuple(scenes),
        timeline=service.list_timeline(
            agent.scope,
            start=clock.now() - timedelta(days=7),
            end=clock.now(),
        ),
        incidents=service.list_incidents(agent.scope),
    )
