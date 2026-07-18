"""DynamoDB repository adapters with tenant-boundary keys and TTL metadata.

The adapter accepts a boto3-compatible Table object, but imports no AWS SDK.
This keeps local tests offline and prevents SDK types from leaking into the
application or domain contracts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any, Mapping, overload

from proofloop.application.models import (
    AgentDefinition,
    AgentScope,
    AssuranceStateCommit,
    ComplianceIncident,
    ComplianceReadModel,
    EvidenceStoreStatus,
    EvidenceStoreWrite,
    TimelineEntry,
)
from proofloop.domain.models import (
    EvidenceEnvelope,
    EvidenceOutcome,
    WorkflowExecutionReference,
)


_CONDITIONAL_NEW_ITEM = "attribute_not_exists(PK) AND attribute_not_exists(SK)"
_EVIDENCE_RETENTION = timedelta(days=8)
_READ_MODEL_RETENTION = timedelta(days=8)
_INCIDENT_RETENTION = timedelta(days=30)
_MAX_TRANSITION_COMMIT_ATTEMPTS = 4


class DynamoProofLoopStore:
    """Single-table implementation of all ProofLoop application repositories."""

    def __init__(self, table: Any) -> None:
        self._table = table

    @overload
    def add(self, definition_or_scope: AgentDefinition) -> bool: ...

    @overload
    def add(
        self,
        definition_or_scope: AgentScope,
        evidence: EvidenceEnvelope,
    ) -> EvidenceStoreWrite: ...

    def add(
        self,
        definition_or_scope: AgentDefinition | AgentScope,
        evidence: EvidenceEnvelope | None = None,
    ) -> bool | EvidenceStoreWrite:
        """Implement the AgentRepository and evidence-repository `add` ports."""

        if isinstance(definition_or_scope, AgentDefinition):
            definition = definition_or_scope
            item = _item(
                definition.scope,
                _agent_sk(definition.scope.agent_id),
                "AGENT",
                definition.model_dump_json(),
                GSI1PK="AGENT_REGISTRY",
                GSI1SK=_registry_sort_key(definition.scope),
            )
            if self._put_if_absent(item):
                return True
            existing = self.get(definition.scope)
            if existing != definition:
                raise ValueError("agent scope is already registered differently")
            return False

        scope: AgentScope = definition_or_scope
        if evidence is None:
            raise TypeError("evidence is required")
        payload = _logical_payload(evidence)
        payload_hash = _hash(payload)
        sk = _evidence_sk(scope.agent_id, evidence)
        evidence_id_sk = _evidence_id_sk(scope.agent_id, evidence.evidence_id)
        item = _item(
            scope,
            sk,
            "EVIDENCE",
            evidence.model_dump_json(),
            ttl=int((evidence.ingested_at + _EVIDENCE_RETENTION).timestamp()),
            payload_hash=payload_hash,
            canonical_evidence_id=evidence.evidence_id,
        )
        id_item = _item(
            scope,
            evidence_id_sk,
            "EVIDENCE_ID",
            evidence.evidence_id,
            ttl=int((evidence.ingested_at + _EVIDENCE_RETENTION).timestamp()),
            canonical_sk=sk,
            payload_hash=payload_hash,
            canonical_evidence_id=evidence.evidence_id,
        )
        try:
            self._table.meta.client.transact_write_items(
                TransactItems=(
                    {
                        "Put": {
                            "TableName": self._table.name,
                            "Item": _encode_item(item),
                            "ConditionExpression": _CONDITIONAL_NEW_ITEM,
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table.name,
                            "Item": _encode_item(id_item),
                            "ConditionExpression": _CONDITIONAL_NEW_ITEM,
                        }
                    },
                )
            )
            return EvidenceStoreWrite(
                status=EvidenceStoreStatus.ACCEPTED,
                canonical_evidence_id=evidence.evidence_id,
            )
        except Exception:
            existing_evidence_item = self._get(scope, sk)
            existing_id_item = self._get(scope, evidence_id_sk)
            if existing_evidence_item is None and existing_id_item is None:
                raise

        if existing_evidence_item is not None:
            if existing_evidence_item.get("payload_hash") != payload_hash:
                self._record_evidence_conflict(scope, sk, evidence, payload_hash)
            return EvidenceStoreWrite(
                status=(
                    EvidenceStoreStatus.DUPLICATE
                    if existing_evidence_item.get("payload_hash") == payload_hash
                    else EvidenceStoreStatus.CONFLICT
                ),
                canonical_evidence_id=str(
                    existing_evidence_item["canonical_evidence_id"]
                ),
            )

        if existing_id_item is None:
            raise RuntimeError("evidence transaction failed without a canonical item")
        canonical_sk = str(existing_id_item["canonical_sk"])
        canonical_item = self._get(scope, canonical_sk)
        if canonical_item is None:
            raise RuntimeError("evidence id index is missing its canonical evidence")
        canonical = EvidenceEnvelope.model_validate_json(str(canonical_item["document"]))
        quarantine = _quarantine_collision(canonical, evidence, payload)
        self._record_evidence_conflict(
            scope,
            canonical_sk,
            quarantine,
            payload_hash,
        )
        return EvidenceStoreWrite(
            status=EvidenceStoreStatus.CONFLICT,
            canonical_evidence_id=str(existing_id_item["canonical_evidence_id"]),
        )

    def get(self, scope: AgentScope) -> AgentDefinition | None:
        item = self._get(scope, _agent_sk(scope.agent_id))
        return (
            AgentDefinition.model_validate_json(str(item["document"]))
            if item is not None
            else None
        )

    def update(self, definition: AgentDefinition) -> None:
        self._table.put_item(
            Item=_item(
                definition.scope,
                _agent_sk(definition.scope.agent_id),
                "AGENT",
                definition.model_dump_json(),
                GSI1PK="AGENT_REGISTRY",
                GSI1SK=_registry_sort_key(definition.scope),
            )
        )

    def list_scopes(self) -> tuple[AgentScope, ...]:
        items: list[Mapping[str, Any]] = []
        kwargs: dict[str, Any] = {
            "IndexName": "AgentRegistryIndex",
            "KeyConditionExpression": "GSI1PK = :registry",
            "ExpressionAttributeValues": {":registry": "AGENT_REGISTRY"},
        }
        while True:
            result = self._table.query(**kwargs)
            items.extend(result.get("Items", ()))
            last_key = result.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        scopes = tuple(
            AgentDefinition.model_validate_json(str(item["document"])).scope
            for item in items
        )
        return tuple(sorted(scopes, key=lambda scope: scope.storage_key))

    def list_for_workflow(
        self,
        scope: AgentScope,
        workflow: WorkflowExecutionReference,
    ) -> tuple[EvidenceEnvelope, ...]:
        events = tuple(
            EvidenceEnvelope.model_validate_json(str(item["document"]))
            for item in self._query_prefix(scope, f"AGENT#{scope.agent_id}#EVIDENCE#")
        )
        return tuple(
            sorted(
                (event for event in events if event.workflow == workflow),
                key=lambda event: (event.observed_at, event.evidence_id),
            )
        )

    def get_compliance(self, scope: AgentScope) -> ComplianceReadModel | None:
        item = self._get(scope, _compliance_sk(scope.agent_id))
        return (
            ComplianceReadModel.model_validate_json(str(item["document"]))
            if item is not None
            else None
        )

    def put_compliance(self, value: ComplianceReadModel) -> None:
        scope = _scope_from_compliance(value)
        self._table.put_item(
            Item=_item(
                scope,
                _compliance_sk(scope.agent_id),
                "COMPLIANCE",
                value.model_dump_json(),
                ttl=int((value.evaluated_at + _READ_MODEL_RETENTION).timestamp()),
            )
        )

    def commit_state(self, value: AssuranceStateCommit) -> bool:
        """Atomically commit one optimistic compliance/timeline/incident update."""

        scope = _scope_from_compliance(value.compliance)
        expected_revision = self._state_revision(scope)
        next_revision = expected_revision + 1
        compliance_item = _item(
            scope,
            _compliance_sk(scope.agent_id),
            "COMPLIANCE",
            value.compliance.model_dump_json(),
            ttl=int(
                (value.compliance.evaluated_at + _READ_MODEL_RETENTION).timestamp()
            ),
        )
        expected = value.expected_compliance
        compliance_put: dict[str, Any] = {
            "TableName": self._table.name,
            "Item": _encode_item(compliance_item),
            "ConditionExpression": (
                _CONDITIONAL_NEW_ITEM
                if expected is None
                else "document = :expected_document"
            ),
        }
        if expected is not None:
            compliance_put["ExpressionAttributeValues"] = {
                ":expected_document": {"S": expected.model_dump_json()}
            }
        operations: list[dict[str, Any]] = [
            {"Put": compliance_put},
            self._revision_put_operation(
                scope,
                expected_revision=expected_revision,
                next_revision=next_revision,
            ),
        ]
        if value.transition is not None:
            transition_item = _item(
                scope,
                _timeline_sk(value.transition, next_revision),
                "TIMELINE",
                value.transition.model_dump_json(),
                ttl=int(value.transition.expires_at.timestamp()),
            )
            operations.append(
                {
                    "Put": {
                        "TableName": self._table.name,
                        "Item": _encode_item(transition_item),
                        "ConditionExpression": _CONDITIONAL_NEW_ITEM,
                    }
                }
            )
        for incident in value.incident_updates:
            retention_start = incident.resolved_at or incident.opened_at
            incident_item = _item(
                scope,
                _incident_sk(scope.agent_id, incident.incident_id),
                "INCIDENT",
                incident.model_dump_json(),
                ttl=int((retention_start + _INCIDENT_RETENTION).timestamp()),
            )
            operations.append(
                {
                    "Put": {
                        "TableName": self._table.name,
                        "Item": _encode_item(incident_item),
                    }
                }
            )
        try:
            self._table.meta.client.transact_write_items(
                TransactItems=operations,
            )
            return True
        except Exception:
            current = self.get_compliance(scope)
            current_revision = self._state_revision(scope)
            if current != expected or current_revision != expected_revision:
                return False
            raise

    def append_if_status_changed(self, value: TimelineEntry) -> bool:
        for _ in range(_MAX_TRANSITION_COMMIT_ATTEMPTS):
            latest = self.latest_transition(value.scope)
            if latest is not None and latest.current_status is value.current_status:
                return False
            expected_revision = self._state_revision(value.scope)
            next_revision = expected_revision + 1
            item = _item(
                value.scope,
                _timeline_sk(value, next_revision),
                "TIMELINE",
                value.model_dump_json(),
                ttl=int(value.expires_at.timestamp()),
            )
            try:
                self._table.meta.client.transact_write_items(
                    TransactItems=(
                        self._revision_put_operation(
                            value.scope,
                            expected_revision=expected_revision,
                            next_revision=next_revision,
                        ),
                        {
                            "Put": {
                                "TableName": self._table.name,
                                "Item": _encode_item(item),
                                "ConditionExpression": _CONDITIONAL_NEW_ITEM,
                            }
                        },
                    )
                )
                return True
            except Exception:
                if self._state_revision(value.scope) != expected_revision:
                    continue
                raise
        raise RuntimeError("transition state changed concurrently; retry safely")

    def latest_transition(self, scope: AgentScope) -> TimelineEntry | None:
        items = self._query_prefix(
            scope,
            f"AGENT#{scope.agent_id}#TIMELINE#",
            scan_forward=False,
            limit=1,
        )
        return (
            TimelineEntry.model_validate_json(str(items[0]["document"]))
            if items
            else None
        )

    def list_timeline(
        self,
        scope: AgentScope,
        start,
        end,
    ) -> tuple[TimelineEntry, ...]:
        values = tuple(
            TimelineEntry.model_validate_json(str(item["document"]))
            for item in self._query_prefix(
                scope,
                f"AGENT#{scope.agent_id}#TIMELINE#",
            )
        )
        return tuple(
            value for value in values if start <= value.evaluated_at <= end
        )

    def create_incident_if_absent(self, value: ComplianceIncident) -> bool:
        return self._put_if_absent(
            _item(
                value.scope,
                _incident_sk(value.scope.agent_id, value.incident_id),
                "INCIDENT",
                value.model_dump_json(),
                ttl=int((value.opened_at + _INCIDENT_RETENTION).timestamp()),
            )
        )

    def put_incident(self, value: ComplianceIncident) -> None:
        retention_start = value.resolved_at or value.opened_at
        self._table.put_item(
            Item=_item(
                value.scope,
                _incident_sk(value.scope.agent_id, value.incident_id),
                "INCIDENT",
                value.model_dump_json(),
                ttl=int((retention_start + _INCIDENT_RETENTION).timestamp()),
            )
        )

    def list_incidents(self, scope: AgentScope) -> tuple[ComplianceIncident, ...]:
        values = tuple(
            ComplianceIncident.model_validate_json(str(item["document"]))
            for item in self._query_prefix(
                scope,
                f"AGENT#{scope.agent_id}#INCIDENT#",
            )
        )
        return tuple(sorted(values, key=lambda item: (item.opened_at, item.incident_id)))

    def _put_if_absent(self, item: dict[str, Any]) -> bool:
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression=_CONDITIONAL_NEW_ITEM,
            )
            return True
        except Exception:
            existing = self._table.get_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                ConsistentRead=True,
            ).get("Item")
            if existing is None:
                raise
            return False

    def _record_evidence_conflict(
        self,
        scope: AgentScope,
        canonical_sk: str,
        evidence: EvidenceEnvelope,
        payload_hash: str,
    ) -> None:
        conflict_item = _item(
            scope,
            f"{canonical_sk}#CONFLICT#{payload_hash}",
            "EVIDENCE_CONFLICT",
            evidence.model_dump_json(),
            ttl=int((evidence.ingested_at + _EVIDENCE_RETENTION).timestamp()),
            payload_hash=payload_hash,
            canonical_evidence_id=evidence.evidence_id,
        )
        self._put_if_absent(conflict_item)

    def _get(self, scope: AgentScope, sk: str) -> Mapping[str, Any] | None:
        result = self._table.get_item(
            Key={"PK": _pk(scope), "SK": sk},
            ConsistentRead=True,
        )
        return result.get("Item")

    def _state_revision(self, scope: AgentScope) -> int:
        item = self._get(scope, _state_revision_sk(scope.agent_id))
        if item is None:
            return 0
        revision = item.get("revision")
        if (
            not isinstance(revision, str)
            or not revision.isascii()
            or not revision.isdigit()
        ):
            raise RuntimeError("assurance state revision is invalid")
        parsed = int(revision)
        if parsed < 1:
            raise RuntimeError("assurance state revision is invalid")
        return parsed

    def _revision_put_operation(
        self,
        scope: AgentScope,
        *,
        expected_revision: int,
        next_revision: int,
    ) -> dict[str, Any]:
        item = _item(
            scope,
            _state_revision_sk(scope.agent_id),
            "STATE_REVISION",
            str(next_revision),
            revision=str(next_revision),
        )
        put: dict[str, Any] = {
            "TableName": self._table.name,
            "Item": _encode_item(item),
            "ConditionExpression": (
                _CONDITIONAL_NEW_ITEM
                if expected_revision == 0
                else "revision = :expected_revision"
            ),
        }
        if expected_revision > 0:
            put["ExpressionAttributeValues"] = {
                ":expected_revision": {"S": str(expected_revision)}
            }
        return {"Put": put}

    def _query_prefix(
        self,
        scope: AgentScope,
        prefix: str,
        *,
        scan_forward: bool = True,
        limit: int | None = None,
    ) -> tuple[Mapping[str, Any], ...]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
            "ExpressionAttributeValues": {":pk": _pk(scope), ":prefix": prefix},
            "ScanIndexForward": scan_forward,
        }
        if limit is not None:
            kwargs["Limit"] = limit
        values: list[Mapping[str, Any]] = []
        while True:
            result = self._table.query(**kwargs)
            values.extend(result.get("Items", ()))
            last_key = result.get("LastEvaluatedKey")
            if not last_key or (limit is not None and len(values) >= limit):
                break
            kwargs["ExclusiveStartKey"] = last_key
        return tuple(values[:limit] if limit is not None else values)


def _pk(scope: AgentScope) -> str:
    return (
        f"TENANT#{scope.tenant_id}#ENV#{scope.environment.value}"
        f"#BOUNDARY#{scope.assurance_boundary_id}"
    )


def _agent_sk(agent_id: str) -> str:
    return f"AGENT#{agent_id}#DEFINITION"


def _registry_sort_key(scope: AgentScope) -> str:
    return (
        f"TENANT#{scope.tenant_id}#ENV#{scope.environment.value}"
        f"#BOUNDARY#{scope.assurance_boundary_id}#AGENT#{scope.agent_id}"
    )


def _compliance_sk(agent_id: str) -> str:
    return f"AGENT#{agent_id}#COMPLIANCE"


def _state_revision_sk(agent_id: str) -> str:
    return f"AGENT#{agent_id}#STATE-REVISION"


def _evidence_sk(agent_id: str, evidence: EvidenceEnvelope) -> str:
    workflow = evidence.workflow
    identity_hash = _hash(
        "\x1f".join(
            (
                workflow.workflow_id,
                workflow.execution_id,
                workflow.trace_id,
                evidence.source,
                evidence.source_event_id,
            )
        )
    )
    return f"AGENT#{agent_id}#EVIDENCE#{identity_hash}"


def _evidence_id_sk(agent_id: str, evidence_id: str) -> str:
    return f"AGENT#{agent_id}#EVIDENCE-ID#{_hash(evidence_id)}"


def _timeline_sk(value: TimelineEntry, revision: int) -> str:
    return (
        f"AGENT#{value.scope.agent_id}#TIMELINE#"
        f"{revision:020d}#{value.transition_id}"
    )


def _incident_sk(agent_id: str, incident_id: str) -> str:
    return f"AGENT#{agent_id}#INCIDENT#{incident_id}"


def _item(
    scope: AgentScope,
    sk: str,
    record_type: str,
    document: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "PK": _pk(scope),
        "SK": sk,
        "record_type": record_type,
        "document": document,
        **extra,
    }


def _encode_item(item: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    encoded: dict[str, dict[str, str]] = {}
    for key, value in item.items():
        if isinstance(value, str):
            encoded[key] = {"S": value}
        elif isinstance(value, int):
            encoded[key] = {"N": str(value)}
        else:
            raise TypeError(f"unsupported DynamoDB transaction value for {key}")
    return encoded


def _scope_from_compliance(value: ComplianceReadModel) -> AgentScope:
    return AgentScope(
        tenant_id=value.tenant_id,
        environment=value.environment,
        assurance_boundary_id=value.assurance_boundary_id,
        agent_id=value.agent_id,
    )


def _logical_payload(evidence: EvidenceEnvelope) -> str:
    value = evidence.model_dump(
        mode="json",
        exclude={"evidence_id", "ingested_at"},
    )
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _quarantine_collision(
    canonical: EvidenceEnvelope,
    conflicting: EvidenceEnvelope,
    payload: str,
) -> EvidenceEnvelope:
    digest = _hash(payload)[:24]
    return conflicting.model_copy(
        update={
            "evidence_id": f"conflict-{digest}",
            "workflow": canonical.workflow,
            "source": canonical.source,
            "source_event_id": canonical.source_event_id,
            "outcome": EvidenceOutcome.INCOMPLETE,
        }
    )
