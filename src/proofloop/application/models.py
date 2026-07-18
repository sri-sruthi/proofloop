"""Immutable application-layer contracts for ProofLoop's vertical slice."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from proofloop.domain.models import (
    AssuranceStatus,
    ControlDefinition,
    Environment,
    IncidentStatus,
    ReasonCode,
    WorkflowExecutionReference,
)


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC-aware")
    return value


class ApplicationModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class AgentScope(ApplicationModel):
    """Tenant-owned identity used on every application repository operation."""

    tenant_id: Identifier
    environment: Environment
    assurance_boundary_id: Identifier
    agent_id: Identifier

    @property
    def storage_key(self) -> tuple[str, str, str, str]:
        return (
            self.tenant_id,
            self.environment.value,
            self.assurance_boundary_id,
            self.agent_id,
        )


class AgentDefinition(ApplicationModel):
    """One registered agent and its PS-6.2 control-to-field mapping."""

    scope: AgentScope
    workflow: WorkflowExecutionReference
    controls: tuple[ControlDefinition, ...] = Field(min_length=1)
    guardrails_control_id: Identifier
    pii_redaction_control_id: Identifier
    audit_logging_control_id: Identifier
    hitl_control_id: Identifier

    @model_validator(mode="after")
    def boundary_and_control_mapping_must_be_exact(self) -> Self:
        if (
            self.scope.tenant_id != self.workflow.tenant_id
            or self.scope.environment is not self.workflow.environment
            or self.scope.assurance_boundary_id
            != self.workflow.assurance_boundary_id
        ):
            raise ValueError("agent scope must match its workflow assurance boundary")
        control_ids = tuple(control.control_id for control in self.controls)
        if len(control_ids) != len(set(control_ids)):
            raise ValueError("agent control_id values must be unique")
        mapped = {
            self.guardrails_control_id,
            self.pii_redaction_control_id,
            self.audit_logging_control_id,
            self.hitl_control_id,
        }
        if not mapped.issubset(set(control_ids)):
            raise ValueError("each PS-6.2 field must map to a declared control")
        return self


class EvidenceIngestStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"


class EvidenceIngestResult(ApplicationModel):
    status: EvidenceIngestStatus
    canonical_evidence_id: Identifier


class EvidenceStoreStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"


class EvidenceStoreWrite(ApplicationModel):
    status: EvidenceStoreStatus
    canonical_evidence_id: Identifier


class ControlCompliance(ApplicationModel):
    control_id: Identifier
    display_name: Identifier
    status: AssuranceStatus
    active: bool | None
    last_evidence_at: datetime | None = None
    reason_codes: tuple[ReasonCode, ...] = Field(min_length=1)
    evidence_ids: tuple[Identifier, ...] = ()

    _last_evidence_at_is_utc = field_validator("last_evidence_at")(
        lambda value: _require_utc(value) if value is not None else value
    )


class ComplianceReadModel(ApplicationModel):
    """Exact PS-6.2 compliance record returned by the application/API."""

    agent_id: Identifier
    tenant_id: Identifier
    environment: Environment
    assurance_boundary_id: Identifier
    guardrails_active: bool | None
    last_violation_timestamp: datetime | None
    pii_redaction_enabled: bool | None
    audit_logging_enabled: bool | None
    hitl_configured: bool | None
    overall_compliance_status: AssuranceStatus
    reason_codes: tuple[ReasonCode, ...] = Field(min_length=1)
    supporting_evidence_ids: tuple[Identifier, ...] = ()
    evaluated_at: datetime
    next_safe_action: Identifier
    controls: tuple[ControlCompliance, ...] = Field(min_length=1)

    _last_violation_is_utc = field_validator("last_violation_timestamp")(
        lambda value: _require_utc(value) if value is not None else value
    )
    _evaluated_at_is_utc = field_validator("evaluated_at")(_require_utc)


class TimelineEntry(ApplicationModel):
    transition_id: Identifier
    scope: AgentScope
    previous_status: AssuranceStatus | None
    current_status: AssuranceStatus
    reason_codes: tuple[ReasonCode, ...] = Field(min_length=1)
    affected_control_ids: tuple[Identifier, ...] = ()
    supporting_evidence_ids: tuple[Identifier, ...] = ()
    summary: Identifier
    next_safe_action: Identifier
    evaluated_at: datetime
    expires_at: datetime

    _evaluated_at_is_utc = field_validator("evaluated_at")(_require_utc)
    _expires_at_is_utc = field_validator("expires_at")(_require_utc)


class IncidentSlaPolicy(ApplicationModel):
    amber_after: timedelta = timedelta(hours=24)
    red_after: timedelta = timedelta(hours=1)

    @field_validator("amber_after", "red_after")
    @classmethod
    def duration_must_be_positive(cls, value: timedelta) -> timedelta:
        if value <= timedelta(0):
            raise ValueError("incident SLA durations must be positive")
        return value


class ComplianceIncident(ApplicationModel):
    incident_id: Identifier
    scope: AgentScope
    workflow: WorkflowExecutionReference
    status: IncidentStatus
    assurance_status: AssuranceStatus
    affected_control_ids: tuple[Identifier, ...] = Field(min_length=1)
    opened_at: datetime
    customer_impact: Identifier
    remediation_steps: Identifier
    resolution_evidence_ids: tuple[Identifier, ...] = ()
    resolved_at: datetime | None = None

    _opened_at_is_utc = field_validator("opened_at")(_require_utc)
    _resolved_at_is_utc = field_validator("resolved_at")(
        lambda value: _require_utc(value) if value is not None else value
    )

    @model_validator(mode="after")
    def resolution_must_be_evidence_backed(self) -> Self:
        if self.status is IncidentStatus.RESOLVED:
            if not self.resolution_evidence_ids or self.resolved_at is None:
                raise ValueError("resolved incidents require evidence and resolved_at")
        elif self.resolution_evidence_ids or self.resolved_at is not None:
            raise ValueError("open incidents cannot contain resolution fields")
        return self


class SyncOutcome(ApplicationModel):
    compliance: ComplianceReadModel
    transition_created: bool
    incident_created: bool


class AssuranceStateCommit(ApplicationModel):
    """One optimistic, all-or-nothing assurance aggregate mutation."""

    expected_compliance: ComplianceReadModel | None
    compliance: ComplianceReadModel
    transition: TimelineEntry | None = None
    incident_updates: tuple[ComplianceIncident, ...] = ()

    @model_validator(mode="after")
    def every_record_must_share_one_scope(self) -> Self:
        scope = AgentScope(
            tenant_id=self.compliance.tenant_id,
            environment=self.compliance.environment,
            assurance_boundary_id=self.compliance.assurance_boundary_id,
            agent_id=self.compliance.agent_id,
        )
        if self.expected_compliance is not None:
            expected_scope = AgentScope(
                tenant_id=self.expected_compliance.tenant_id,
                environment=self.expected_compliance.environment,
                assurance_boundary_id=self.expected_compliance.assurance_boundary_id,
                agent_id=self.expected_compliance.agent_id,
            )
            if expected_scope != scope:
                raise ValueError("expected and replacement compliance scopes must match")
        if self.transition is not None and self.transition.scope != scope:
            raise ValueError("transition scope must match compliance scope")
        if any(incident.scope != scope for incident in self.incident_updates):
            raise ValueError("incident scopes must match compliance scope")
        return self
