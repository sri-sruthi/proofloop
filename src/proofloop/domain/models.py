"""Typed, immutable, cloud-neutral domain contracts for ProofLoop."""

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


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _require_utc(value: datetime) -> datetime:
    """Reject naive and non-UTC timestamps at the domain boundary."""

    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC-aware")
    return value


class DomainModel(BaseModel):
    """Base settings shared by all external and domain contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class EvidenceOutcome(str, Enum):
    """Outcome asserted by a normalized evidence event."""

    # B105 is inapplicable: PASS is a public assurance outcome, not a password.
    PASS = "PASS"  # nosec B105
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceType(str, Enum):
    """Portable evidence categories understood by the domain core."""

    CONTROL_CONFIGURATION = "CONTROL_CONFIGURATION"
    CONTROL_EXECUTION = "CONTROL_EXECUTION"
    CONTROL_OUTCOME = "CONTROL_OUTCOME"
    AUDIT_EVENT = "AUDIT_EVENT"
    CANARY_RESULT = "CANARY_RESULT"


class AssuranceStatus(str, Enum):
    """Assignment-compatible assurance status."""

    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class Environment(str, Enum):
    """Cloud-neutral deployment environment within an assurance boundary."""

    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class ReasonCode(str, Enum):
    """Stable, machine-readable reasons for an assurance decision."""

    ALL_REQUIRED_EVIDENCE_VERIFIED = "ALL_REQUIRED_EVIDENCE_VERIFIED"
    REQUIRED_EVIDENCE_MISSING = "REQUIRED_EVIDENCE_MISSING"
    EVIDENCE_STALE = "EVIDENCE_STALE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_UNCORRELATED = "EVIDENCE_UNCORRELATED"
    OBSOLETE_PROVENANCE = "OBSOLETE_PROVENANCE"
    CONTROL_FAILURE_OBSERVED = "CONTROL_FAILURE_OBSERVED"
    REMEDIATION_UNVERIFIED = "REMEDIATION_UNVERIFIED"
    CLOCK_SKEW_EXCEEDED = "CLOCK_SKEW_EXCEEDED"
    NO_CONTROLS_DECLARED = "NO_CONTROLS_DECLARED"


class CanarySafetyMode(str, Enum):
    """Only execution modes incapable of real customer effects are legal."""

    NO_OP = "NO_OP"
    SANDBOX = "SANDBOX"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Provenance(DomainModel):
    """Exact component version vector used to validate an evidence claim.

    Deterministic components set genuinely inapplicable agent/model/tool fields
    to ``None``. Agent/model evidence populates every applicable optional field.
    """

    component_version: Identifier
    prompt_version: Identifier | None = None
    model_version: Identifier | None = None
    policy_version: Identifier
    schema_version: Identifier
    tool_catalog_version: Identifier | None = None
    mcp_server_version: Identifier | None = None
    orchestration_version: Identifier
    guardrail_version: Identifier | None = None
    runtime_config_version: Identifier


class WorkflowExecutionReference(DomainModel):
    """Exact tenant and execution boundary to which evidence belongs."""

    tenant_id: Identifier
    environment: Environment
    assurance_boundary_id: Identifier
    workflow_id: Identifier
    execution_id: Identifier
    trace_id: Identifier


class EvidenceFreshnessPolicy(DomainModel):
    """Maximum age at which evidence can still support a current claim."""

    max_age: timedelta
    clock_skew_tolerance: timedelta = timedelta(seconds=5)

    @field_validator("max_age")
    @classmethod
    def max_age_must_be_positive(cls, value: timedelta) -> timedelta:
        if value <= timedelta(0):
            raise ValueError("max_age must be greater than zero")
        return value

    @field_validator("clock_skew_tolerance")
    @classmethod
    def skew_tolerance_cannot_be_negative(cls, value: timedelta) -> timedelta:
        if value < timedelta(0):
            raise ValueError("clock_skew_tolerance cannot be negative")
        return value


class RequiredEvidenceSpecification(DomainModel):
    """One evidence obligation declared by a control."""

    requirement_id: Identifier
    evidence_type: EvidenceType
    freshness: EvidenceFreshnessPolicy
    expected_provenance: Provenance
    minimum_count: int = Field(default=1, ge=1)
    required_source: Identifier | None = None


class ControlDefinition(DomainModel):
    """Customer-owned definition of a required runtime control."""

    control_id: Identifier
    display_name: Identifier
    required_evidence: tuple[RequiredEvidenceSpecification, ...] = Field(min_length=1)
    verification_required_after: datetime | None = None
    customer_impact: Identifier
    next_safe_action: Identifier

    _verification_time_is_utc = field_validator("verification_required_after")(
        lambda value: _require_utc(value) if value is not None else value
    )

    @model_validator(mode="after")
    def requirement_ids_must_be_unique(self) -> Self:
        requirement_ids = tuple(
            requirement.requirement_id for requirement in self.required_evidence
        )
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("required_evidence requirement_id values must be unique")
        return self


EvidenceScalar = str | int | float | bool | None


class EvidenceAttribute(DomainModel):
    """One canonical, deeply immutable scalar evidence attribute."""

    key: Identifier
    value: EvidenceScalar


class EvidenceEnvelope(DomainModel):
    """Immutable normalized observation used by assurance evaluation."""

    evidence_id: Identifier
    control_id: Identifier
    requirement_id: Identifier
    evidence_type: EvidenceType
    source: Identifier
    source_event_id: Identifier
    workflow: WorkflowExecutionReference
    outcome: EvidenceOutcome
    observed_at: datetime
    ingested_at: datetime
    provenance: Provenance
    attributes: tuple[EvidenceAttribute, ...] = ()

    _observed_at_is_utc = field_validator("observed_at")(_require_utc)
    _ingested_at_is_utc = field_validator("ingested_at")(_require_utc)

    @field_validator("attributes")
    @classmethod
    def attributes_are_unique_and_canonical(
        cls,
        value: tuple[EvidenceAttribute, ...],
    ) -> tuple[EvidenceAttribute, ...]:
        keys = tuple(attribute.key for attribute in value)
        if len(keys) != len(set(keys)):
            raise ValueError("evidence attribute keys must be unique")
        return tuple(sorted(value, key=lambda attribute: attribute.key))


class StateTransitionExplanation(DomainModel):
    """Machine- and customer-readable explanation of an assurance result."""

    previous_status: AssuranceStatus | None = None
    current_status: AssuranceStatus
    reason_codes: tuple[ReasonCode, ...] = Field(min_length=1)
    affected_control_ids: tuple[Identifier, ...] = ()
    supporting_evidence_ids: tuple[Identifier, ...] = ()
    summary: Identifier
    next_safe_action: Identifier
    evaluated_at: datetime

    _evaluated_at_is_utc = field_validator("evaluated_at")(_require_utc)

    @model_validator(mode="after")
    def status_reason_and_controls_must_agree(self) -> Self:
        success_reason = ReasonCode.ALL_REQUIRED_EVIDENCE_VERIFIED
        no_controls_reason = ReasonCode.NO_CONTROLS_DECLARED
        if self.current_status is AssuranceStatus.GREEN:
            if self.reason_codes != (success_reason,):
                raise ValueError("GREEN requires only ALL_REQUIRED_EVIDENCE_VERIFIED")
            if self.affected_control_ids:
                raise ValueError("GREEN cannot contain affected controls")
            return self

        if success_reason in self.reason_codes:
            raise ValueError("non-GREEN cannot contain a success reason")
        if not self.affected_control_ids:
            if self.reason_codes != (no_controls_reason,):
                raise ValueError("non-GREEN requires an affected control")
        elif no_controls_reason in self.reason_codes:
            raise ValueError("NO_CONTROLS_DECLARED cannot name affected controls")
        return self


class AssuranceEvaluation(DomainModel):
    """Complete output of one deterministic evaluation cycle."""

    status: AssuranceStatus
    explanation: StateTransitionExplanation
    considered_evidence_ids: tuple[Identifier, ...] = ()
    ignored_duplicate_evidence_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def status_must_match_explanation(self) -> Self:
        if self.status is not self.explanation.current_status:
            raise ValueError("status must equal explanation.current_status")
        return self


class IncidentRecord(DomainModel):
    """Customer-visible incident raised from a sustained assurance problem."""

    incident_id: Identifier
    workflow: WorkflowExecutionReference
    status: IncidentStatus
    affected_control_ids: tuple[Identifier, ...] = Field(min_length=1)
    opened_at: datetime
    customer_impact: Identifier
    next_safe_action: Identifier
    resolution_evidence_ids: tuple[Identifier, ...] = ()

    _opened_at_is_utc = field_validator("opened_at")(_require_utc)

    @model_validator(mode="after")
    def resolved_incident_requires_evidence(self) -> Self:
        if self.status is IncidentStatus.RESOLVED and not self.resolution_evidence_ids:
            raise ValueError("RESOLVED incidents require resolution evidence")
        return self


class CanaryDefinition(DomainModel):
    """A reserved synthetic control probe with a safe execution boundary."""

    canary_id: Identifier
    control_id: Identifier
    display_name: Identifier
    evidence_type: EvidenceType
    expected_outcome: EvidenceOutcome
    safety_mode: CanarySafetyMode
    next_safe_action: Identifier


class CanaryResult(DomainModel):
    """Observed result of a safe canary execution."""

    canary_id: Identifier
    run_id: Identifier
    workflow: WorkflowExecutionReference
    started_at: datetime
    completed_at: datetime
    outcome: EvidenceOutcome
    evidence_ids: tuple[Identifier, ...] = ()
    side_effects_confirmed_absent: bool

    _started_at_is_utc = field_validator("started_at")(_require_utc)
    _completed_at_is_utc = field_validator("completed_at")(_require_utc)

    @model_validator(mode="after")
    def completion_cannot_precede_start(self) -> Self:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if (
            self.outcome is EvidenceOutcome.PASS
            and not self.side_effects_confirmed_absent
        ):
            raise ValueError("PASS canaries require confirmed absence of side effects")
        return self


class IdentityPrincipal(DomainModel):
    """Authenticated actor identity exposed to domain use cases."""

    tenant_id: Identifier
    subject_id: Identifier
    roles: tuple[Identifier, ...] = Field(min_length=1)
