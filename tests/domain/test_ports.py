from __future__ import annotations

from datetime import datetime, timezone

import proofloop.domain.ports as ports
from proofloop.domain.models import (
    CanaryDefinition,
    CanaryResult,
    ControlDefinition,
    EvidenceEnvelope,
    IdentityPrincipal,
    IncidentRecord,
    StateTransitionExplanation,
    WorkflowExecutionReference,
)


class InMemoryEvidenceRepository:
    def add(self, evidence: EvidenceEnvelope) -> bool:
        return True

    def list_for_execution(
        self,
        workflow: WorkflowExecutionReference,
    ) -> tuple[EvidenceEnvelope, ...]:
        return ()


class InMemoryControlRepository:
    def list_for_workflow(
        self,
        tenant_id: str,
        workflow_id: str,
    ) -> tuple[ControlDefinition, ...]:
        return ()


class RecordingEventPublisher:
    def publish_transition(self, transition: StateTransitionExplanation) -> None:
        return None


class SafeCanaryExecutor:
    def execute(
        self,
        canary: CanaryDefinition,
        workflow: WorkflowExecutionReference,
    ) -> CanaryResult:
        raise NotImplementedError


class RecordingNotificationPort:
    def notify_incident(self, incident: IncidentRecord) -> None:
        return None


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


class RequestIdentityContext:
    def current_principal(self) -> IdentityPrincipal:
        raise NotImplementedError


evidence_repository: ports.EvidenceRepository = InMemoryEvidenceRepository()
control_repository: ports.ControlRepository = InMemoryControlRepository()
event_publisher: ports.EventPublisher = RecordingEventPublisher()
canary_executor: ports.CanaryExecutor = SafeCanaryExecutor()
notification_port: ports.NotificationPort = RecordingNotificationPort()
clock: ports.Clock = FixedClock()
identity_context: ports.IdentityContext = RequestIdentityContext()


def test_ports_support_structural_implementations_without_cloud_types() -> None:
    assert isinstance(InMemoryEvidenceRepository(), ports.EvidenceRepository)
    assert isinstance(InMemoryControlRepository(), ports.ControlRepository)
    assert isinstance(RecordingEventPublisher(), ports.EventPublisher)
    assert isinstance(SafeCanaryExecutor(), ports.CanaryExecutor)
    assert isinstance(RecordingNotificationPort(), ports.NotificationPort)
    assert isinstance(FixedClock(), ports.Clock)
    assert isinstance(RequestIdentityContext(), ports.IdentityContext)
