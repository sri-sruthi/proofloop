"""Deterministic in-memory adapters for local development and tests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import overload

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


class VirtualClock:
    """UTC virtual clock that advances without sleeping."""

    def __init__(self, value: datetime) -> None:
        self._value: datetime
        self.set(value)

    def now(self) -> datetime:
        return self._value

    def set(self, value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("virtual clock must be UTC-aware")
        if hasattr(self, "_value") and value < self._value:
            raise ValueError("virtual clock cannot move backwards")
        self._value = value

    def advance(self, duration: timedelta) -> datetime:
        if duration < timedelta(0):
            raise ValueError("virtual clock cannot move backwards")
        self._value += duration
        return self._value


class SystemClock:
    """UTC wall clock for local HTTP and Lambda composition."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class InMemoryProofLoopStore:
    """One process-local implementation of every application repository port."""

    def __init__(self) -> None:
        self._state_lock = RLock()
        self._agents: dict[tuple[str, str, str, str], AgentDefinition] = {}
        self._evidence: dict[
            tuple[str, ...], EvidenceEnvelope
        ] = {}
        self._evidence_payloads: dict[
            tuple[str, ...], str
        ] = {}
        self._conflicting_evidence: dict[
            tuple[tuple[str, ...], str], EvidenceEnvelope
        ] = {}
        self._evidence_ids: dict[tuple[tuple[str, str, str, str], str], str] = {}
        self._evidence_by_id: dict[
            tuple[tuple[str, str, str, str], str], EvidenceEnvelope
        ] = {}
        self._compliance: dict[
            tuple[str, str, str, str], ComplianceReadModel
        ] = {}
        self._timeline: dict[tuple[str, str, str, str], list[TimelineEntry]] = {}
        self._incidents: dict[
            tuple[tuple[str, str, str, str], str], ComplianceIncident
        ] = {}

    @property
    def evidence_count(self) -> int:
        return len(self._evidence)

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
        """Implement both AgentRepository.add and ApplicationEvidenceRepository.add."""

        if isinstance(definition_or_scope, AgentDefinition):
            definition = definition_or_scope
            agent_key = definition.scope.storage_key
            existing_agent = self._agents.get(agent_key)
            if existing_agent is not None:
                if existing_agent != definition:
                    raise ValueError("agent scope is already registered differently")
                return False
            self._agents[agent_key] = definition
            return True

        scope: AgentScope = definition_or_scope
        if evidence is None:
            raise TypeError("evidence is required")
        evidence_key = (
            *scope.storage_key,
            evidence.workflow.workflow_id,
            evidence.workflow.execution_id,
            evidence.workflow.trace_id,
            evidence.source,
            evidence.source_event_id,
        )
        payload = _logical_payload(evidence)
        existing_id_payload = self._evidence_ids.get(
            (scope.storage_key, evidence.evidence_id)
        )
        if existing_id_payload is not None and existing_id_payload != payload:
            canonical = self._evidence_by_id[(scope.storage_key, evidence.evidence_id)]
            canonical_key = _evidence_key(scope, canonical)
            quarantine = _quarantine_collision(canonical, evidence, payload)
            self._conflicting_evidence[(canonical_key, payload)] = quarantine
            return EvidenceStoreWrite(
                status=EvidenceStoreStatus.CONFLICT,
                canonical_evidence_id=canonical.evidence_id,
            )
        existing_evidence = self._evidence.get(evidence_key)
        if existing_evidence is not None:
            status = (
                EvidenceStoreStatus.DUPLICATE
                if self._evidence_payloads[evidence_key] == payload
                else EvidenceStoreStatus.CONFLICT
            )
            if status is EvidenceStoreStatus.CONFLICT:
                self._conflicting_evidence[(evidence_key, payload)] = evidence
            return EvidenceStoreWrite(
                status=status,
                canonical_evidence_id=existing_evidence.evidence_id,
            )
        self._evidence[evidence_key] = evidence
        self._evidence_payloads[evidence_key] = payload
        self._evidence_ids[(scope.storage_key, evidence.evidence_id)] = payload
        self._evidence_by_id[(scope.storage_key, evidence.evidence_id)] = evidence
        return EvidenceStoreWrite(
            status=EvidenceStoreStatus.ACCEPTED,
            canonical_evidence_id=evidence.evidence_id,
        )

    def get(self, scope: AgentScope) -> AgentDefinition | None:
        return self._agents.get(scope.storage_key)

    def update(self, definition: AgentDefinition) -> None:
        if definition.scope.storage_key not in self._agents:
            raise KeyError("agent is not registered")
        self._agents[definition.scope.storage_key] = definition

    def list_scopes(self) -> tuple[AgentScope, ...]:
        return tuple(
            self._agents[key].scope
            for key in sorted(self._agents)
        )

    def list_for_workflow(
        self,
        scope: AgentScope,
        workflow: WorkflowExecutionReference,
    ) -> tuple[EvidenceEnvelope, ...]:
        return tuple(
            sorted(
                (
                    event
                    for key, event in self._evidence.items()
                    if key[:4] == scope.storage_key and event.workflow == workflow
                ),
                key=lambda event: (event.observed_at, event.evidence_id),
            )
            + sorted(
                (
                    event
                    for (key, _), event in self._conflicting_evidence.items()
                    if key[:4] == scope.storage_key and event.workflow == workflow
                ),
                key=lambda event: (event.observed_at, event.evidence_id),
            )
        )

    def get_compliance(self, scope: AgentScope) -> ComplianceReadModel | None:
        return self._compliance.get(scope.storage_key)

    def put_compliance(self, value: ComplianceReadModel) -> None:
        key = (
            value.tenant_id,
            value.environment.value,
            value.assurance_boundary_id,
            value.agent_id,
        )
        self._compliance[key] = value

    def commit_state(self, value: AssuranceStateCommit) -> bool:
        scope_key = (
            value.compliance.tenant_id,
            value.compliance.environment.value,
            value.compliance.assurance_boundary_id,
            value.compliance.agent_id,
        )
        with self._state_lock:
            if self._compliance.get(scope_key) != value.expected_compliance:
                return False
            self._compliance[scope_key] = value.compliance
            if value.transition is not None:
                self._timeline.setdefault(scope_key, []).append(value.transition)
            for incident in value.incident_updates:
                self._incidents[(scope_key, incident.incident_id)] = incident
            return True

    def append_if_status_changed(self, value: TimelineEntry) -> bool:
        entries = self._timeline.setdefault(value.scope.storage_key, [])
        if entries and entries[-1].current_status is value.current_status:
            return False
        entries.append(value)
        return True

    def latest_transition(self, scope: AgentScope) -> TimelineEntry | None:
        entries = self._timeline.get(scope.storage_key, [])
        return entries[-1] if entries else None

    def list_timeline(
        self,
        scope: AgentScope,
        start: datetime,
        end: datetime,
    ) -> tuple[TimelineEntry, ...]:
        return tuple(
            entry
            for entry in self._timeline.get(scope.storage_key, [])
            if start <= entry.evaluated_at <= end
        )

    def create_incident_if_absent(self, value: ComplianceIncident) -> bool:
        key = (value.scope.storage_key, value.incident_id)
        if key in self._incidents:
            return False
        self._incidents[key] = value
        return True

    def put_incident(self, value: ComplianceIncident) -> None:
        self._incidents[(value.scope.storage_key, value.incident_id)] = value

    def list_incidents(self, scope: AgentScope) -> tuple[ComplianceIncident, ...]:
        return tuple(
            sorted(
                (
                    incident
                    for (scope_key, _), incident in self._incidents.items()
                    if scope_key == scope.storage_key
                ),
                key=lambda incident: (incident.opened_at, incident.incident_id),
            )
        )


def _logical_payload(evidence: EvidenceEnvelope) -> str:
    value = evidence.model_dump(
        mode="json",
        exclude={"evidence_id", "ingested_at"},
    )
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _evidence_key(scope: AgentScope, evidence: EvidenceEnvelope) -> tuple[str, ...]:
    return (
        *scope.storage_key,
        evidence.workflow.workflow_id,
        evidence.workflow.execution_id,
        evidence.workflow.trace_id,
        evidence.source,
        evidence.source_event_id,
    )


def _quarantine_collision(
    canonical: EvidenceEnvelope,
    conflicting: EvidenceEnvelope,
    payload: str,
) -> EvidenceEnvelope:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    return conflicting.model_copy(
        update={
            "evidence_id": f"conflict-{digest}",
            "workflow": canonical.workflow,
            "source": canonical.source,
            "source_event_id": canonical.source_event_id,
            "outcome": EvidenceOutcome.INCOMPLETE,
        }
    )
