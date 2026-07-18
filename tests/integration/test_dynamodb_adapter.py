from __future__ import annotations

from datetime import timedelta

from .tests_support import (
    START,
    build_compliance,
    build_incident,
    build_timeline,
    make_agent,
    make_evidence,
)
from proofloop.application.models import (
    AssuranceStateCommit,
    EvidenceStoreStatus,
    IncidentSlaPolicy,
)
from proofloop.application.scenario import build_demo_agent, seed_fresh_passes
from proofloop.application.service import ProofLoopService
from proofloop.domain.models import AssuranceStatus, EvidenceOutcome, ReasonCode
from proofloop.infrastructure.dynamodb import DynamoProofLoopStore
from proofloop.infrastructure.memory import VirtualClock


class ConditionalFailure(Exception):
    pass


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict] = {}
        self.scan_calls = 0
        self.name = "proofloop-test"
        self.meta = _FakeMeta(self)

    def put_item(self, *, Item, ConditionExpression=None):
        key = (Item["PK"], Item["SK"])
        if ConditionExpression and key in self.items:
            raise ConditionalFailure("conditional check failed")
        self.items[key] = dict(Item)
        return {}

    def get_item(self, *, Key, ConsistentRead=False):
        item = self.items.get((Key["PK"], Key["SK"]))
        return {"Item": dict(item)} if item is not None else {}

    def query(self, **kwargs):
        if kwargs.get("IndexName") == "AgentRegistryIndex":
            registry = kwargs["ExpressionAttributeValues"][":registry"]
            rows = [
                dict(item)
                for item in self.items.values()
                if item.get("GSI1PK") == registry
            ]
            rows.sort(key=lambda item: item["GSI1SK"])
            return {"Items": rows}
        pk = kwargs["ExpressionAttributeValues"][":pk"]
        prefix = kwargs["ExpressionAttributeValues"][":prefix"]
        rows = [
            dict(item)
            for (item_pk, item_sk), item in self.items.items()
            if item_pk == pk and item_sk.startswith(prefix)
        ]
        rows.sort(key=lambda item: item["SK"], reverse=not kwargs.get("ScanIndexForward", True))
        limit = kwargs.get("Limit")
        return {"Items": rows[:limit] if limit is not None else rows}

    def scan(self, **kwargs):
        self.scan_calls += 1
        return {"Items": [dict(item) for item in self.items.values()]}


class _FakeMeta:
    def __init__(self, table: FakeTable) -> None:
        self.client = _FakeDynamoClient(table)


class _FakeDynamoClient:
    def __init__(self, table: FakeTable) -> None:
        self._table = table

    def transact_write_items(self, *, TransactItems):
        staged = {key: dict(value) for key, value in self._table.items.items()}
        for operation in TransactItems:
            put = operation["Put"]
            item = {key: _decode(value) for key, value in put["Item"].items()}
            key = (item["PK"], item["SK"])
            condition = put.get("ConditionExpression")
            if condition == "attribute_not_exists(PK) AND attribute_not_exists(SK)":
                if key in staged:
                    raise ConditionalFailure("transaction condition failed")
            elif condition == "document = :expected_document":
                expected = _decode(put["ExpressionAttributeValues"][":expected_document"])
                if staged.get(key, {}).get("document") != expected:
                    raise ConditionalFailure("transaction condition failed")
            elif condition == "revision = :expected_revision":
                expected = _decode(put["ExpressionAttributeValues"][":expected_revision"])
                if staged.get(key, {}).get("revision") != expected:
                    raise ConditionalFailure("transaction condition failed")
            staged[key] = item
        self._table.items = staged
        return {}


def _decode(value):
    if "S" in value:
        return value["S"]
    if "N" in value:
        return int(value["N"])
    raise AssertionError(f"unexpected DynamoDB value: {value}")


def test_evidence_keys_are_tenant_environment_boundary_scoped_with_ttl() -> None:
    table = FakeTable()
    store = DynamoProofLoopStore(table)
    agent = make_agent()
    event = make_evidence(agent, "pii-redaction")

    result = store.add(agent.scope, event)

    assert result.status is EvidenceStoreStatus.ACCEPTED
    item = next(item for item in table.items.values() if item["record_type"] == "EVIDENCE")
    assert item["PK"] == "TENANT#tenant-a#ENV#TEST#BOUNDARY#tenant-a-test-invoices"
    assert item["SK"].startswith("AGENT#invoice-agent#EVIDENCE#")
    assert item["ttl"] == int((START + timedelta(days=8)).timestamp())
    assert "invoice" not in item.get("raw_payload", "")


def test_conditional_evidence_write_is_idempotent_and_detects_conflict() -> None:
    store = DynamoProofLoopStore(FakeTable())
    agent = make_agent()
    first = make_evidence(
        agent,
        "pii-redaction",
        evidence_id="first",
        source_event_id="same",
    )
    duplicate = first.model_copy(update={"evidence_id": "retry"})
    conflict = first.model_copy(
        update={"evidence_id": "conflict", "outcome": EvidenceOutcome.FAIL}
    )

    assert store.add(agent.scope, first).status is EvidenceStoreStatus.ACCEPTED
    assert store.add(agent.scope, duplicate).status is EvidenceStoreStatus.DUPLICATE
    assert store.add(agent.scope, conflict).status is EvidenceStoreStatus.CONFLICT
    retained = store.list_for_workflow(agent.scope, agent.workflow)
    assert {item.evidence_id: item for item in retained} == {
        "first": first,
        "conflict": conflict,
    }


def test_conflicting_evidence_is_quarantined_for_evaluation() -> None:
    store = DynamoProofLoopStore(FakeTable())
    agent = make_agent()
    first = make_evidence(
        agent,
        "pii-redaction",
        evidence_id="first",
        source_event_id="same",
    )
    conflict = first.model_copy(
        update={"evidence_id": "conflict", "outcome": EvidenceOutcome.FAIL}
    )

    assert store.add(agent.scope, first).status is EvidenceStoreStatus.ACCEPTED
    assert store.add(agent.scope, conflict).status is EvidenceStoreStatus.CONFLICT

    retained = store.list_for_workflow(agent.scope, agent.workflow)
    assert {item.evidence_id: item for item in retained} == {
        "first": first,
        "conflict": conflict,
    }


def test_source_event_identity_includes_full_workflow_execution() -> None:
    store = DynamoProofLoopStore(FakeTable())
    agent = make_agent()
    first = make_evidence(agent, "pii-redaction", source_event_id="reused")
    next_workflow = agent.workflow.model_copy(
        update={"execution_id": "next-execution", "trace_id": "next-trace"}
    )
    next_execution = first.model_copy(
        update={
            "evidence_id": "next-evidence",
            "workflow": next_workflow,
        }
    )

    assert store.add(agent.scope, first).status is EvidenceStoreStatus.ACCEPTED
    assert (
        store.add(agent.scope, next_execution).status
        is EvidenceStoreStatus.ACCEPTED
    )


def test_evidence_reference_is_unique_and_conflict_is_retained() -> None:
    store = DynamoProofLoopStore(FakeTable())
    agent = make_agent()
    first = make_evidence(
        agent,
        "pii-redaction",
        evidence_id="shared-reference",
        source_event_id="first-source",
    )
    reused = first.model_copy(update={"source_event_id": "second-source"})

    assert store.add(agent.scope, first).status is EvidenceStoreStatus.ACCEPTED
    result = store.add(agent.scope, reused)

    assert result.status is EvidenceStoreStatus.CONFLICT
    assert result.canonical_evidence_id == "shared-reference"
    retained = store.list_for_workflow(agent.scope, agent.workflow)
    assert len(retained) == 2


def test_all_application_records_round_trip_without_aws_types() -> None:
    table = FakeTable()
    store = DynamoProofLoopStore(table)
    agent = make_agent()
    assert store.add(agent) is True
    assert store.add(agent) is False
    assert store.get(agent.scope) == agent
    assert store.list_scopes() == (agent.scope,)
    assert table.scan_calls == 0

    compliance = build_compliance(agent)
    store.put_compliance(compliance)
    assert store.get_compliance(agent.scope) == compliance

    green = build_timeline(agent)
    assert store.append_if_status_changed(green) is True
    assert store.append_if_status_changed(green) is False
    assert store.latest_transition(agent.scope) == green
    assert store.list_timeline(
        agent.scope,
        START - timedelta(minutes=1),
        START + timedelta(minutes=1),
    ) == (green,)

    incident = build_incident(agent)
    assert store.create_incident_if_absent(incident) is True
    assert store.create_incident_if_absent(incident) is False
    assert store.list_incidents(agent.scope) == (incident,)


def test_atomic_state_commit_rejects_stale_green_after_newer_red() -> None:
    store = DynamoProofLoopStore(FakeTable())
    agent = make_agent()
    store.add(agent)
    green = build_compliance(agent)
    green_transition = build_timeline(agent)
    assert store.commit_state(
        AssuranceStateCommit(
            expected_compliance=None,
            compliance=green,
            transition=green_transition,
        )
    )

    red_time = START + timedelta(minutes=2)
    red = green.model_copy(
        update={
            "overall_compliance_status": AssuranceStatus.RED,
            "reason_codes": (ReasonCode.CONTROL_FAILURE_OBSERVED,),
            "evaluated_at": red_time,
            "next_safe_action": "Stop relying on the failed control and inspect it.",
        }
    )
    red_transition = green_transition.model_copy(
        update={
            "transition_id": "transition-red",
            "previous_status": AssuranceStatus.GREEN,
            "current_status": AssuranceStatus.RED,
            "reason_codes": (ReasonCode.CONTROL_FAILURE_OBSERVED,),
            "evaluated_at": red_time,
            "expires_at": red_time + timedelta(days=7),
        }
    )
    assert store.commit_state(
        AssuranceStateCommit(
            expected_compliance=green,
            compliance=red,
            transition=red_transition,
        )
    )

    stale_green = green.model_copy(
        update={"evaluated_at": START + timedelta(minutes=1)}
    )
    assert not store.commit_state(
        AssuranceStateCommit(
            expected_compliance=green,
            compliance=stale_green,
        )
    )
    assert store.get_compliance(agent.scope) == red
    assert store.list_timeline(
        agent.scope,
        START - timedelta(seconds=1),
        red_time + timedelta(seconds=1),
    ) == (green_transition, red_transition)


def test_same_clock_transitions_keep_commit_order_and_amber_sla_start() -> None:
    table = FakeTable()
    store = DynamoProofLoopStore(table)
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
            amber_after=timedelta(hours=24),
            red_after=timedelta(minutes=30),
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
    assert service.sync(agent.scope).compliance.overall_compliance_status is AssuranceStatus.GREEN

    clock.advance(timedelta(hours=25))
    assert service.sync(agent.scope).compliance.overall_compliance_status is AssuranceStatus.AMBER
    clock.advance(timedelta(hours=23))
    service.record_canary_result(
        agent.scope,
        control_id="guardrails",
        outcome=EvidenceOutcome.FAIL,
        source_event_id="same-clock-failure",
    )
    assert service.sync(agent.scope).compliance.overall_compliance_status is AssuranceStatus.RED
    service.mark_remediated(agent.scope, control_ids=("guardrails",))
    assert service.sync(agent.scope).compliance.overall_compliance_status is AssuranceStatus.AMBER

    timeline = service.list_timeline(
        agent.scope,
        start=START - timedelta(seconds=1),
        end=clock.now(),
    )
    assert [item.current_status for item in timeline] == [
        AssuranceStatus.GREEN,
        AssuranceStatus.AMBER,
        AssuranceStatus.RED,
        AssuranceStatus.AMBER,
    ]
    assert store.latest_transition(agent.scope) == timeline[-1]

    clock.advance(timedelta(hours=24, minutes=1))
    outcome = service.sync(agent.scope)
    assert outcome.incident_created is True
    assert service.list_incidents(agent.scope)[0].assurance_status is AssuranceStatus.AMBER
    revision = next(
        item
        for item in table.items.values()
        if item["record_type"] == "STATE_REVISION"
    )
    assert revision["revision"] == "5"
