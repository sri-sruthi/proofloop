"""Cloud-neutral dependency ports for ProofLoop."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable

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


@runtime_checkable
class EvidenceRepository(Protocol):
    """Persist and retrieve normalized evidence without exposing storage types."""

    def add(self, evidence: EvidenceEnvelope) -> bool:
        """Store evidence idempotently and report whether it was newly added."""

    def list_for_execution(
        self,
        workflow: WorkflowExecutionReference,
    ) -> Sequence[EvidenceEnvelope]:
        """Return evidence associated with an exact workflow execution."""


@runtime_checkable
class ControlRepository(Protocol):
    """Retrieve customer-owned control declarations."""

    def list_for_workflow(
        self,
        tenant_id: str,
        workflow_id: str,
    ) -> Sequence[ControlDefinition]:
        """Return controls configured for one tenant workflow."""


@runtime_checkable
class EventPublisher(Protocol):
    """Publish explainable assurance state transitions."""

    def publish_transition(self, transition: StateTransitionExplanation) -> None:
        """Publish one immutable transition explanation."""


@runtime_checkable
class CanaryExecutor(Protocol):
    """Execute a reserved no-op or sandbox canary."""

    def execute(
        self,
        canary: CanaryDefinition,
        workflow: WorkflowExecutionReference,
    ) -> CanaryResult:
        """Run a safe canary for an exact workflow execution."""


@runtime_checkable
class NotificationPort(Protocol):
    """Notify customers or operators about a domain incident."""

    def notify_incident(self, incident: IncidentRecord) -> None:
        """Deliver one incident notification."""


@runtime_checkable
class Clock(Protocol):
    """Supply evaluation time without coupling the evaluator to wall time."""

    def now(self) -> datetime:
        """Return the current UTC-aware time."""


@runtime_checkable
class IdentityContext(Protocol):
    """Expose the authenticated principal without leaking framework types."""

    def current_principal(self) -> IdentityPrincipal:
        """Return the principal bound to the current request or operation."""
