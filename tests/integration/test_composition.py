from __future__ import annotations

from proofloop.api.app import ProofLoopApi
from proofloop.infrastructure.composition import build_application, build_service
from proofloop.infrastructure.memory import InMemoryProofLoopStore, VirtualClock
from .tests_support import START


def test_local_composition_seeds_one_usable_demo_agent(monkeypatch) -> None:
    monkeypatch.setenv("PROOFLOOP_API_KEY", "local-key")
    store = InMemoryProofLoopStore()
    clock = VirtualClock(START)

    service = build_service(store=store, clock=clock, seed_demo=True)
    app = build_application(service=service)

    assert isinstance(app, ProofLoopApi)
    assert len(service.list_agent_scopes()) == 1
    scope = service.list_agent_scopes()[0]
    assert service.sync(scope).compliance.overall_compliance_status.value == "GREEN"


def test_default_memory_composition_is_locally_usable(monkeypatch) -> None:
    monkeypatch.delenv("PROOFLOOP_EVIDENCE_TABLE_NAME", raising=False)
    monkeypatch.delenv("PROOFLOOP_SEED_DEMO", raising=False)

    service = build_service()

    assert len(service.list_agent_scopes()) == 1
