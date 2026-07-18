"""Deterministic ingestion, sync, timeline, canary, and incident use cases."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Sequence

from proofloop.application.errors import ApplicationError, ErrorCode
from proofloop.application.models import (
    AgentDefinition,
    AgentScope,
    AssuranceStateCommit,
    ComplianceIncident,
    ComplianceReadModel,
    ControlCompliance,
    EvidenceIngestResult,
    EvidenceIngestStatus,
    EvidenceStoreStatus,
    IncidentSlaPolicy,
    SyncOutcome,
    TimelineEntry,
)
from proofloop.application.ports import (
    AgentRepository,
    ApplicationEvidenceRepository,
    AssuranceStateRepository,
    ComplianceRepository,
    IncidentRepository,
    TimelineRepository,
)
from proofloop.domain.evaluator import evaluate_assurance
from proofloop.domain.models import (
    AssuranceEvaluation,
    AssuranceStatus,
    ControlDefinition,
    EvidenceAttribute,
    EvidenceEnvelope,
    EvidenceOutcome,
    EvidenceType,
    IncidentStatus,
    WorkflowExecutionReference,
)
from proofloop.domain.ports import Clock


_SAFE_ATTRIBUTE_KEYS = frozenset(
    {
        "audit_recorded",
        "canary_safe",
        "configuration_active",
        "control_active",
        "human_approval_required",
        "redaction_applied",
        "schema_valid",
        "side_effects_absent",
        "synthetic",
    }
)
_OPAQUE_EVIDENCE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,127}$")
_SSN_SHAPED_REFERENCE = re.compile(r"^\d{3}-\d{2}-\d{4}$")
_MAX_SYNC_COMMIT_ATTEMPTS = 4


class ProofLoopService:
    """Application facade with no framework or AWS dependency."""

    def __init__(
        self,
        *,
        agents: AgentRepository,
        evidence: ApplicationEvidenceRepository,
        compliance: ComplianceRepository,
        timeline: TimelineRepository,
        incidents: IncidentRepository,
        state: AssuranceStateRepository,
        clock: Clock,
        incident_sla: IncidentSlaPolicy | None = None,
    ) -> None:
        self._agents = agents
        self._evidence = evidence
        self._compliance = compliance
        self._timeline = timeline
        self._incidents = incidents
        self._state = state
        self._clock = clock
        self._incident_sla = incident_sla or IncidentSlaPolicy()

    def register_agent(self, definition: AgentDefinition) -> bool:
        return self._agents.add(definition)

    def ingest_evidence(
        self,
        scope: AgentScope,
        evidence: EvidenceEnvelope,
    ) -> EvidenceIngestResult:
        definition = self._require_agent(scope)
        self._validate_evidence_boundary(definition, evidence.workflow)
        self._validate_declared_evidence(definition, evidence)
        self._validate_safe_metadata(evidence)
        self._validate_canary_attestation(evidence)

        normalized_evidence = evidence.model_copy(
            update={"ingested_at": self._clock.now()}
        )

        stored = self._evidence.add(scope, normalized_evidence)
        if stored.status is EvidenceStoreStatus.CONFLICT:
            raise ApplicationError(
                ErrorCode.EVIDENCE_CONFLICT,
                "The source event identifier was already used for different evidence.",
            )
        status = (
            EvidenceIngestStatus.ACCEPTED
            if stored.status is EvidenceStoreStatus.ACCEPTED
            else EvidenceIngestStatus.DUPLICATE
        )
        return EvidenceIngestResult(
            status=status,
            canonical_evidence_id=stored.canonical_evidence_id,
        )

    def sync(self, scope: AgentScope) -> SyncOutcome:
        definition = self._require_agent(scope)
        for _ in range(_MAX_SYNC_COMMIT_ATTEMPTS):
            events = tuple(
                self._evidence.list_for_workflow(scope, definition.workflow)
            )
            previous = self._compliance.get_compliance(scope)
            evaluation = evaluate_assurance(
                controls=definition.controls,
                evidence=events,
                workflow=definition.workflow,
                clock=self._clock,
                previous_status=(
                    previous.overall_compliance_status
                    if previous is not None
                    else None
                ),
            )
            now = evaluation.explanation.evaluated_at
            read_model = self._build_read_model(
                definition,
                events,
                evaluation,
            )
            transition = self._build_transition(
                scope,
                previous,
                read_model,
                now,
                evaluation.explanation.summary,
            )
            incident_updates, incident_created = self._plan_incident_updates(
                definition,
                read_model,
                transition,
                now,
            )
            if self._state.commit_state(
                AssuranceStateCommit(
                    expected_compliance=previous,
                    compliance=read_model,
                    transition=transition,
                    incident_updates=incident_updates,
                )
            ):
                return SyncOutcome(
                    compliance=read_model,
                    transition_created=transition is not None,
                    incident_created=incident_created,
                )
        raise ApplicationError(
            ErrorCode.INTERNAL_ERROR,
            "Assurance state changed concurrently; retry the sync safely.",
        )

    def get_compliance(self, scope: AgentScope) -> ComplianceReadModel:
        self._require_agent(scope)
        value = self._compliance.get_compliance(scope)
        if value is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "No compliance record exists yet; run a sync first.",
            )
        return value

    def list_timeline(
        self,
        scope: AgentScope,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[TimelineEntry, ...]:
        self._require_agent(scope)
        if start > end:
            raise ApplicationError(
                ErrorCode.INVALID_REQUEST,
                "Timeline start must not be after end.",
            )
        return tuple(self._timeline.list_timeline(scope, start, end))

    def list_incidents(self, scope: AgentScope) -> tuple[ComplianceIncident, ...]:
        self._require_agent(scope)
        return tuple(self._incidents.list_incidents(scope))

    def list_agent_scopes(self) -> tuple[AgentScope, ...]:
        return tuple(self._agents.list_scopes())

    def now(self) -> datetime:
        """Expose the injected clock to delivery adapters without wall-clock drift."""

        return self._clock.now()

    def mark_remediated(
        self,
        scope: AgentScope,
        *,
        control_ids: Sequence[str],
        at: datetime | None = None,
    ) -> AgentDefinition:
        definition = self._require_agent(scope)
        boundary = at or self._clock.now()
        if boundary.tzinfo is None or boundary.utcoffset() != timedelta(0):
            raise ApplicationError(
                ErrorCode.INVALID_REQUEST,
                "Remediation time must be a UTC-aware timestamp.",
            )
        selected = set(control_ids)
        known = {control.control_id for control in definition.controls}
        if not selected or not selected.issubset(known):
            raise ApplicationError(
                ErrorCode.INVALID_REQUEST,
                "Remediation must name one or more declared controls.",
            )
        updated_controls = tuple(
            control.model_copy(update={"verification_required_after": boundary})
            if control.control_id in selected
            else control
            for control in definition.controls
        )
        updated = definition.model_copy(update={"controls": updated_controls})
        self._agents.update(updated)
        return updated

    def record_canary_result(
        self,
        scope: AgentScope,
        *,
        control_id: str,
        outcome: EvidenceOutcome,
        source_event_id: str,
    ) -> EvidenceIngestResult:
        definition = self._require_agent(scope)
        control = next(
            (item for item in definition.controls if item.control_id == control_id),
            None,
        )
        if control is None:
            raise ApplicationError(
                ErrorCode.EVIDENCE_NOT_DECLARED,
                "The canary control is not declared for this agent.",
            )
        requirements = tuple(
            requirement
            for requirement in control.required_evidence
            if requirement.evidence_type is EvidenceType.CANARY_RESULT
        )
        if len(requirements) != 1:
            raise ApplicationError(
                ErrorCode.EVIDENCE_NOT_DECLARED,
                "The control must declare exactly one safe canary requirement.",
            )
        requirement = requirements[0]
        now = self._clock.now()
        evidence = EvidenceEnvelope(
            evidence_id=f"canary-{source_event_id}",
            control_id=control.control_id,
            requirement_id=requirement.requirement_id,
            evidence_type=EvidenceType.CANARY_RESULT,
            source=requirement.required_source or "safe-canary",
            source_event_id=source_event_id,
            workflow=definition.workflow,
            outcome=outcome,
            observed_at=now,
            ingested_at=now,
            provenance=requirement.expected_provenance,
            attributes=(
                EvidenceAttribute(key="side_effects_absent", value=True),
                EvidenceAttribute(key="synthetic", value=True),
            ),
        )
        return self.ingest_evidence(scope, evidence)

    def _control_record(
        self,
        control: ControlDefinition,
        events: Sequence[EvidenceEnvelope],
        workflow: WorkflowExecutionReference,
    ) -> ControlCompliance:
        evaluation = evaluate_assurance(
            controls=(control,),
            evidence=events,
            workflow=workflow,
            clock=self._clock,
        )
        relevant_times = tuple(
            event.observed_at
            for event in events
            if event.workflow == workflow and event.control_id == control.control_id
        )
        active = {
            AssuranceStatus.GREEN: True,
            AssuranceStatus.AMBER: None,
            AssuranceStatus.RED: False,
        }[evaluation.status]
        return ControlCompliance(
            control_id=control.control_id,
            display_name=control.display_name,
            status=evaluation.status,
            active=active,
            last_evidence_at=max(relevant_times) if relevant_times else None,
            reason_codes=evaluation.explanation.reason_codes,
            evidence_ids=evaluation.explanation.supporting_evidence_ids,
        )

    def _build_read_model(
        self,
        definition: AgentDefinition,
        events: Sequence[EvidenceEnvelope],
        evaluation: AssuranceEvaluation,
    ) -> ComplianceReadModel:
        control_records = tuple(
            self._control_record(control, events, definition.workflow)
            for control in sorted(
                definition.controls,
                key=lambda item: item.control_id,
            )
        )
        by_id = {record.control_id: record for record in control_records}
        violation_times = tuple(
            event.observed_at
            for event in events
            if event.workflow == definition.workflow
            and event.outcome is EvidenceOutcome.FAIL
        )
        return ComplianceReadModel(
            agent_id=definition.scope.agent_id,
            tenant_id=definition.scope.tenant_id,
            environment=definition.scope.environment,
            assurance_boundary_id=definition.scope.assurance_boundary_id,
            guardrails_active=by_id[definition.guardrails_control_id].active,
            last_violation_timestamp=max(violation_times) if violation_times else None,
            pii_redaction_enabled=by_id[definition.pii_redaction_control_id].active,
            audit_logging_enabled=by_id[definition.audit_logging_control_id].active,
            hitl_configured=by_id[definition.hitl_control_id].active,
            overall_compliance_status=evaluation.status,
            reason_codes=evaluation.explanation.reason_codes,
            supporting_evidence_ids=(
                evaluation.explanation.supporting_evidence_ids
            ),
            evaluated_at=evaluation.explanation.evaluated_at,
            next_safe_action=evaluation.explanation.next_safe_action,
            controls=control_records,
        )

    @staticmethod
    def _build_transition(
        scope: AgentScope,
        previous: ComplianceReadModel | None,
        compliance: ComplianceReadModel,
        now: datetime,
        summary: str,
    ) -> TimelineEntry | None:
        previous_status = (
            previous.overall_compliance_status if previous is not None else None
        )
        if previous_status is compliance.overall_compliance_status:
            return None
        return TimelineEntry(
            transition_id=_stable_id(
                "transition",
                *scope.storage_key,
                compliance.overall_compliance_status.value,
                now.isoformat(),
            ),
            scope=scope,
            previous_status=previous_status,
            current_status=compliance.overall_compliance_status,
            reason_codes=compliance.reason_codes,
            affected_control_ids=tuple(
                record.control_id
                for record in compliance.controls
                if record.status is not AssuranceStatus.GREEN
            ),
            supporting_evidence_ids=compliance.supporting_evidence_ids,
            summary=summary,
            next_safe_action=compliance.next_safe_action,
            evaluated_at=now,
            expires_at=now + timedelta(days=7),
        )

    def _plan_incident_updates(
        self,
        definition: AgentDefinition,
        compliance: ComplianceReadModel,
        transition: TimelineEntry | None,
        now: datetime,
    ) -> tuple[tuple[ComplianceIncident, ...], bool]:
        existing = tuple(self._incidents.list_incidents(definition.scope))
        unresolved = tuple(
            incident
            for incident in existing
            if incident.status is not IncidentStatus.RESOLVED
        )
        if compliance.overall_compliance_status is AssuranceStatus.GREEN:
            return (
                tuple(
                    incident.model_copy(
                        update={
                            "status": IncidentStatus.RESOLVED,
                            "resolution_evidence_ids": (
                                compliance.supporting_evidence_ids
                            ),
                            "resolved_at": now,
                        }
                    )
                    for incident in unresolved
                ),
                False,
            )

        affected_ids = tuple(
            record.control_id
            for record in compliance.controls
            if record.status is not AssuranceStatus.GREEN
        )
        customer_impact = " ".join(
            control.customer_impact
            for control in definition.controls
            if control.control_id in affected_ids
        )
        if unresolved:
            updates = tuple(
                incident.model_copy(
                    update={
                        "assurance_status": compliance.overall_compliance_status,
                        "affected_control_ids": affected_ids,
                        "customer_impact": customer_impact,
                        "remediation_steps": compliance.next_safe_action,
                    }
                )
                for incident in unresolved
                if incident.assurance_status
                is not compliance.overall_compliance_status
                or incident.affected_control_ids != affected_ids
                or incident.remediation_steps != compliance.next_safe_action
            )
            return updates, False

        latest = self._timeline.latest_transition(definition.scope)
        state_started_at = (
            transition.evaluated_at
            if transition is not None
            else (
                latest.evaluated_at
                if latest is not None
                and latest.current_status
                is compliance.overall_compliance_status
                else None
            )
        )
        if state_started_at is None:
            return (), False
        threshold = (
            self._incident_sla.amber_after
            if compliance.overall_compliance_status is AssuranceStatus.AMBER
            else self._incident_sla.red_after
        )
        if now - state_started_at < threshold:
            return (), False
        incident_id = _stable_id(
            "incident",
            *definition.scope.storage_key,
            compliance.overall_compliance_status.value,
            state_started_at.isoformat(),
        )
        if any(incident.incident_id == incident_id for incident in existing):
            return (), False
        return (
            (
                ComplianceIncident(
                    incident_id=incident_id,
                    scope=definition.scope,
                    workflow=definition.workflow,
                    status=IncidentStatus.OPEN,
                    assurance_status=compliance.overall_compliance_status,
                    affected_control_ids=affected_ids,
                    opened_at=now,
                    customer_impact=customer_impact,
                    remediation_steps=compliance.next_safe_action,
                ),
            ),
            True,
        )

    def _require_agent(self, scope: AgentScope) -> AgentDefinition:
        definition = self._agents.get(scope)
        if definition is None:
            raise ApplicationError(
                ErrorCode.AGENT_NOT_FOUND,
                "No agent is registered for this tenant and assurance boundary.",
            )
        return definition

    @staticmethod
    def _validate_evidence_boundary(
        definition: AgentDefinition,
        workflow: WorkflowExecutionReference,
    ) -> None:
        expected = definition.workflow
        if (
            expected.tenant_id != workflow.tenant_id
            or expected.environment is not workflow.environment
            or expected.assurance_boundary_id != workflow.assurance_boundary_id
        ):
            raise ApplicationError(
                ErrorCode.BOUNDARY_MISMATCH,
                "Evidence belongs to a different tenant, environment, or assurance boundary.",
            )
        if expected != workflow:
            raise ApplicationError(
                ErrorCode.WORKFLOW_MISMATCH,
                "Evidence does not match the registered workflow execution.",
            )

    @staticmethod
    def _validate_declared_evidence(
        definition: AgentDefinition,
        evidence: EvidenceEnvelope,
    ) -> None:
        control = next(
            (item for item in definition.controls if item.control_id == evidence.control_id),
            None,
        )
        if control is None:
            raise ApplicationError(
                ErrorCode.EVIDENCE_NOT_DECLARED,
                "Evidence names a control that is not declared for this agent.",
            )
        requirement = next(
            (
                item
                for item in control.required_evidence
                if item.requirement_id == evidence.requirement_id
            ),
            None,
        )
        if (
            requirement is None
            or requirement.evidence_type is not evidence.evidence_type
            or (
                requirement.required_source is not None
                and requirement.required_source != evidence.source
            )
            or requirement.expected_provenance != evidence.provenance
        ):
            raise ApplicationError(
                ErrorCode.EVIDENCE_NOT_DECLARED,
                "Evidence does not match a declared requirement, source, type, and provenance.",
            )

    @staticmethod
    def _validate_safe_metadata(evidence: EvidenceEnvelope) -> None:
        unsafe_reference = any(
            not _OPAQUE_EVIDENCE_REFERENCE.fullmatch(value)
            or _SSN_SHAPED_REFERENCE.fullmatch(value) is not None
            for value in (evidence.evidence_id, evidence.source_event_id)
        )
        unsafe_attributes = any(
            attribute.key not in _SAFE_ATTRIBUTE_KEYS
            or type(attribute.value) is not bool
            for attribute in evidence.attributes
        )
        if unsafe_reference or unsafe_attributes:
            raise ApplicationError(
                ErrorCode.UNSAFE_EVIDENCE_PAYLOAD,
                "Evidence may contain only bounded opaque references and approved boolean control metadata; raw invoice or PII data is not accepted.",
            )

    @staticmethod
    def _validate_canary_attestation(evidence: EvidenceEnvelope) -> None:
        if evidence.evidence_type is not EvidenceType.CANARY_RESULT:
            return
        attributes = {
            attribute.key: attribute.value for attribute in evidence.attributes
        }
        if (
            attributes.get("synthetic") is not True
            or attributes.get("side_effects_absent") is not True
        ):
            raise ApplicationError(
                ErrorCode.UNSAFE_CANARY_EVIDENCE,
                "Canary evidence requires a declared synthetic probe with confirmed absence of side effects.",
            )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"
