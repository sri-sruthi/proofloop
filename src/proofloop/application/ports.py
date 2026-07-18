"""Cloud-neutral repository ports used by ProofLoop application services."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable

from proofloop.application.models import (
    AgentDefinition,
    AgentScope,
    AssuranceStateCommit,
    ComplianceIncident,
    ComplianceReadModel,
    EvidenceStoreWrite,
    TimelineEntry,
)
from proofloop.domain.models import EvidenceEnvelope, WorkflowExecutionReference
from proofloop.domain.ports import Clock


@runtime_checkable
class AgentRepository(Protocol):
    def add(self, definition: AgentDefinition) -> bool: ...
    def get(self, scope: AgentScope) -> AgentDefinition | None: ...
    def update(self, definition: AgentDefinition) -> None: ...
    def list_scopes(self) -> Sequence[AgentScope]: ...


@runtime_checkable
class ApplicationEvidenceRepository(Protocol):
    def add(
        self,
        scope: AgentScope,
        evidence: EvidenceEnvelope,
    ) -> EvidenceStoreWrite: ...

    def list_for_workflow(
        self,
        scope: AgentScope,
        workflow: WorkflowExecutionReference,
    ) -> Sequence[EvidenceEnvelope]: ...


@runtime_checkable
class ComplianceRepository(Protocol):
    def get_compliance(self, scope: AgentScope) -> ComplianceReadModel | None: ...
    def put_compliance(self, value: ComplianceReadModel) -> None: ...


@runtime_checkable
class AssuranceStateRepository(Protocol):
    def commit_state(self, value: AssuranceStateCommit) -> bool:
        """Atomically apply a sync if expected compliance is still current."""


@runtime_checkable
class TimelineRepository(Protocol):
    def append_if_status_changed(self, value: TimelineEntry) -> bool: ...
    def latest_transition(self, scope: AgentScope) -> TimelineEntry | None: ...
    def list_timeline(
        self,
        scope: AgentScope,
        start: datetime,
        end: datetime,
    ) -> Sequence[TimelineEntry]: ...


@runtime_checkable
class IncidentRepository(Protocol):
    def create_incident_if_absent(self, value: ComplianceIncident) -> bool: ...
    def put_incident(self, value: ComplianceIncident) -> None: ...
    def list_incidents(self, scope: AgentScope) -> Sequence[ComplianceIncident]: ...


__all__ = [
    "AgentRepository",
    "ApplicationEvidenceRepository",
    "Clock",
    "ComplianceRepository",
    "AssuranceStateRepository",
    "IncidentRepository",
    "TimelineRepository",
]
