"""Outer-boundary integration between invoice agents and ProofLoop evidence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from proofloop.agents.guardrails import (
    ControlKey,
    ControlObservation,
    ControlOutcome,
)
from proofloop.agents.contracts import (
    ContentType,
    ExtractedInvoice,
    InvoiceInput,
    TrustedInvoiceMetadata,
)
from proofloop.agents.execution import AgentFailure, ExecutionLimits, FailureCategory
from proofloop.agents.mcp.tool_specs import (
    DuplicateCheckTool,
    HumanReviewRequest,
    HumanReviewTicket,
    HumanReviewTool,
    PurchaseOrderTool,
    ToolError,
    ToolTimeoutError,
    VendorTool,
)
from proofloop.agents.model_provider import (
    ModelProvider,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from proofloop.agents.policy import PolicyConfig
from proofloop.agents.workflow import (
    InvoiceWorkflowResult,
    ModelCallStats,
    PromptBinding,
    ToolCallRecord,
    ToolInvocationOutcome,
    WorkflowStage,
    WorkflowStatus,
    run_invoice_workflow,
)
from proofloop.api.invoice_runs import (
    EvidenceReceipt,
    InvoiceRunRequest,
    InvoiceRunResponse,
    ModelUsageSummary,
    SafeToolCallSummary,
)
from proofloop.application.errors import ApplicationError, ErrorCode
from proofloop.application.models import (
    AgentDefinition,
    AgentScope,
    ComplianceReadModel,
)
from proofloop.application.service import ProofLoopService
from proofloop.domain.models import (
    ControlDefinition,
    Environment,
    EvidenceAttribute,
    EvidenceEnvelope,
    EvidenceFreshnessPolicy,
    EvidenceOutcome,
    EvidenceType,
    Provenance,
    RequiredEvidenceSpecification,
    WorkflowExecutionReference,
)


RUNTIME_SOURCE = "proofloop.agents.guardrails"
CANARY_SOURCE = "proofloop.safe_canary"


class AgentIntegrationSettings(BaseModel):
    """Customer boundary and exact version labels used by definition and emitter."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    tenant_id: str
    environment: Environment
    assurance_boundary_id: str
    agent_id: str
    workflow_id: str = "integrated-invoice-workflow"
    execution_id: str = "invoice-runtime"
    trace_id: str = "invoice-agent-assurance"
    component_version: str = "proofloop-agent-integration-v1"
    prompt_version: str = "1.0.0"
    model_version: str = "fake-model-v0"
    policy_version: str = "invoice-policy-v1"
    schema_version: str = "invoice-contracts-v1"
    tool_catalog_version: str = "invoice-tools-v1"
    orchestration_version: str = "invoice-workflow-v1"
    guardrail_version: str = "invoice-guardrail-v1"
    runtime_config_version: str = "invoice-runtime-v1"
    freshness: timedelta = Field(default=timedelta(hours=24))

    @model_validator(mode="after")
    def freshness_must_be_positive(self) -> Self:
        if self.freshness <= timedelta(0):
            raise ValueError("freshness must be positive")
        return self

    def workflow(self) -> WorkflowExecutionReference:
        return WorkflowExecutionReference(
            tenant_id=self.tenant_id,
            environment=self.environment,
            assurance_boundary_id=self.assurance_boundary_id,
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            trace_id=self.trace_id,
        )

    def runtime_provenance(
        self,
        *,
        prompt_version: str | None = None,
        model_version: str | None = None,
        guardrail_version: str | None = None,
    ) -> Provenance:
        return Provenance(
            component_version=self.component_version,
            prompt_version=prompt_version or self.prompt_version,
            model_version=model_version or self.model_version,
            policy_version=self.policy_version,
            schema_version=self.schema_version,
            tool_catalog_version=self.tool_catalog_version,
            mcp_server_version=None,
            orchestration_version=self.orchestration_version,
            guardrail_version=guardrail_version or self.guardrail_version,
            runtime_config_version=self.runtime_config_version,
        )

    def canary_provenance(self) -> Provenance:
        return Provenance(
            component_version="proofloop-safe-canary-v1",
            prompt_version=None,
            model_version=None,
            policy_version=self.policy_version,
            schema_version=self.schema_version,
            tool_catalog_version=None,
            mcp_server_version=None,
            orchestration_version="proofloop-safe-canary-v1",
            guardrail_version=self.guardrail_version,
            runtime_config_version=self.runtime_config_version,
        )


_MAPPING: dict[ControlKey, tuple[str, str, EvidenceType, str]] = {
    ControlKey.PII_REDACTION: (
        "invoice-pii-redaction",
        "invoice-pii-redaction-runtime",
        EvidenceType.CONTROL_EXECUTION,
        "redaction_applied",
    ),
    ControlKey.AUDIT_LOGGING: (
        "invoice-audit-logging",
        "invoice-audit-logging-runtime",
        EvidenceType.AUDIT_EVENT,
        "audit_recorded",
    ),
    ControlKey.HITL_BOUNDARY: (
        "invoice-hitl-boundary",
        "invoice-hitl-boundary-runtime",
        EvidenceType.CONTROL_OUTCOME,
        "control_active",
    ),
    ControlKey.EXTRACTION_SCHEMA_VALIDATION: (
        "invoice-extraction-guardrail",
        "invoice-extraction-schema-runtime",
        EvidenceType.CONTROL_OUTCOME,
        "schema_valid",
    ),
}


@dataclass
class _FailClosedHumanReviewTool:
    """Let the workflow finish safely while retaining a typed routing failure."""

    inner: HumanReviewTool
    failure_outcome: ToolInvocationOutcome | None = None

    def request_human_review(
        self,
        request: HumanReviewRequest,
    ) -> HumanReviewTicket:
        try:
            return self.inner.request_human_review(request)
        except ToolTimeoutError:
            self.failure_outcome = ToolInvocationOutcome.TIMEOUT
        except ToolError:
            self.failure_outcome = ToolInvocationOutcome.ERROR
        return HumanReviewTicket(
            ticket_id="unpersisted-human-review-failure",
            document_id=request.document_id,
            status="UNAVAILABLE",
            idempotency_key=request.idempotency_key,
        )


@dataclass(frozen=True)
class _CappedModelProvider:
    """Clamp the agent request to the deployment-configured output-token cap."""

    inner: ModelProvider
    max_output_tokens: int

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        bounded = request.model_copy(
            update={
                "max_output_tokens": min(
                    request.max_output_tokens,
                    self.max_output_tokens,
                )
            }
        )
        return self.inner.generate_structured(bounded)


@dataclass
class InvoiceAgentRunner:
    """Run the agent, emit safe evidence, sync, and return a bounded summary."""

    service: ProofLoopService
    settings: AgentIntegrationSettings
    provider_factory: Callable[[InvoiceRunRequest], ModelProvider]
    purchase_order_tool: PurchaseOrderTool
    vendor_tool: VendorTool
    duplicate_tool: DuplicateCheckTool
    human_review_tool: HumanReviewTool
    limits: ExecutionLimits = field(default_factory=ExecutionLimits)
    max_output_tokens: int = 2_000
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    seed_safe_canary: bool = True
    agent: AgentDefinition = field(init=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_output_tokens <= 2_000:
            raise ValueError("max_output_tokens must be between 1 and 2000")
        self.agent = build_integrated_invoice_agent(self.settings)
        newly_registered = self.service.register_agent(self.agent)
        if newly_registered and self.seed_safe_canary:
            canary = run_safe_extraction_canary(
                settings=self.settings,
                agent=self.agent,
                observed_at=self.service.now(),
            )
            self.service.ingest_evidence(self.agent.scope, canary)

    def run_invoice(
        self,
        scope: AgentScope,
        request: InvoiceRunRequest,
    ) -> InvoiceRunResponse:
        if scope != self.agent.scope:
            raise ApplicationError(
                ErrorCode.AGENT_NOT_FOUND,
                "No invoice workflow is registered for this assurance scope.",
            )
        invoice = InvoiceInput(
            document_id=request.document_id,
            content_type=ContentType(request.content_type.value),
            trusted_metadata=TrustedInvoiceMetadata(
                source_system=request.source_system,
                received_at=request.received_at,
                declared_vendor_hint=request.declared_vendor_hint,
            ),
            untrusted_content=request.invoice_content,
        )
        human_review = _FailClosedHumanReviewTool(self.human_review_tool)
        result = run_invoice_workflow(
            invoice=invoice,
            provider=_CappedModelProvider(
                self.provider_factory(request),
                self.max_output_tokens,
            ),
            purchase_order_tool=self.purchase_order_tool,
            vendor_tool=self.vendor_tool,
            duplicate_tool=self.duplicate_tool,
            human_review_tool=human_review,
            limits=self.limits,
            config=self.policy,
            now=self.service.now,
        )
        if human_review.failure_outcome is not None:
            result = _fail_closed_human_review(result, human_review.failure_outcome)
        receipts: list[EvidenceReceipt] = []
        conflict: ApplicationError | None = None
        for observation in result.control_observations:
            evidence = map_control_observation(
                settings=self.settings,
                agent=self.agent,
                document_id=result.document_id,
                prompt_binding=result.prompt_binding,
                model_stats=result.model_stats,
                observation=observation,
            )
            try:
                ingested = self.service.ingest_evidence(scope, evidence)
            except ApplicationError as error:
                if error.code is not ErrorCode.EVIDENCE_CONFLICT:
                    raise
                conflict = conflict or error
                continue
            receipts.append(
                EvidenceReceipt(
                    control_id=evidence.control_id,
                    requirement_id=evidence.requirement_id,
                    evidence_id=ingested.canonical_evidence_id,
                    ingest_status=ingested.status.value,
                )
            )
        compliance = self.service.sync(scope).compliance
        if conflict is not None:
            raise conflict
        return _safe_response(result, tuple(receipts), compliance)


def build_integrated_invoice_agent(
    settings: AgentIntegrationSettings,
) -> AgentDefinition:
    """Build the exact runtime-plus-safe-canary invoice assurance definition."""

    scope = AgentScope(
        tenant_id=settings.tenant_id,
        environment=settings.environment,
        assurance_boundary_id=settings.assurance_boundary_id,
        agent_id=settings.agent_id,
    )
    runtime_provenance = settings.runtime_provenance()
    freshness = EvidenceFreshnessPolicy(max_age=settings.freshness)

    controls = (
        _control(
            control_id="invoice-pii-redaction",
            display_name="Invoice PII redaction",
            requirements=(
                RequiredEvidenceSpecification(
                    requirement_id="invoice-pii-redaction-runtime",
                    evidence_type=EvidenceType.CONTROL_EXECUTION,
                    freshness=freshness,
                    expected_provenance=runtime_provenance,
                    required_source=RUNTIME_SOURCE,
                ),
            ),
            customer_impact="Raw personal data could reach a model or retained system.",
        ),
        _control(
            control_id="invoice-audit-logging",
            display_name="Invoice audit logging",
            requirements=(
                RequiredEvidenceSpecification(
                    requirement_id="invoice-audit-logging-runtime",
                    evidence_type=EvidenceType.AUDIT_EVENT,
                    freshness=freshness,
                    expected_provenance=runtime_provenance,
                    required_source=RUNTIME_SOURCE,
                ),
            ),
            customer_impact="Reviewers could lose proof of a consequential workflow run.",
        ),
        _control(
            control_id="invoice-hitl-boundary",
            display_name="Invoice human-review boundary",
            requirements=(
                RequiredEvidenceSpecification(
                    requirement_id="invoice-hitl-boundary-runtime",
                    evidence_type=EvidenceType.CONTROL_OUTCOME,
                    freshness=freshness,
                    expected_provenance=runtime_provenance,
                    required_source=RUNTIME_SOURCE,
                ),
            ),
            customer_impact="An unsafe invoice disposition could bypass a human reviewer.",
        ),
        _control(
            control_id="invoice-extraction-guardrail",
            display_name="Invoice extraction schema guardrail",
            requirements=(
                RequiredEvidenceSpecification(
                    requirement_id="invoice-extraction-schema-runtime",
                    evidence_type=EvidenceType.CONTROL_OUTCOME,
                    freshness=freshness,
                    expected_provenance=runtime_provenance,
                    required_source=RUNTIME_SOURCE,
                ),
                RequiredEvidenceSpecification(
                    requirement_id="invoice-extraction-safe-canary",
                    evidence_type=EvidenceType.CANARY_RESULT,
                    freshness=freshness,
                    expected_provenance=settings.canary_provenance(),
                    required_source=CANARY_SOURCE,
                ),
            ),
            customer_impact="Malformed model output could be mistaken for a valid invoice.",
        ),
    )
    return AgentDefinition(
        scope=scope,
        workflow=settings.workflow(),
        controls=controls,
        guardrails_control_id="invoice-extraction-guardrail",
        pii_redaction_control_id="invoice-pii-redaction",
        audit_logging_control_id="invoice-audit-logging",
        hitl_control_id="invoice-hitl-boundary",
    )


def map_control_observation(
    *,
    settings: AgentIntegrationSettings,
    agent: AgentDefinition,
    document_id: str,
    prompt_binding: PromptBinding,
    model_stats: ModelCallStats,
    observation: ControlObservation,
) -> EvidenceEnvelope:
    """Translate one observation to one declaration-bound, privacy-safe event."""

    control_id, requirement_id, evidence_type, safe_key = _MAPPING[
        observation.control_key
    ]
    requirement = _requirement(agent, control_id, requirement_id)
    provenance = settings.runtime_provenance(
        prompt_version=prompt_binding.version,
        model_version=model_stats.provider_id or settings.model_version,
        guardrail_version=observation.guardrail_version,
    )
    if provenance != requirement.expected_provenance:
        # The service would reject it later; fail at the bridge with no payload data.
        raise ValueError("agent observation provenance does not match its declaration")
    digest = _stable_digest(
        agent.workflow.tenant_id,
        agent.workflow.environment.value,
        agent.workflow.assurance_boundary_id,
        agent.workflow.workflow_id,
        agent.workflow.execution_id,
        agent.workflow.trace_id,
        document_id,
        observation.control_key.value,
        observation.observed_at.isoformat(),
    )
    outcome = EvidenceOutcome(observation.outcome.value)
    return EvidenceEnvelope(
        evidence_id=f"agent-evidence-{digest}",
        control_id=control_id,
        requirement_id=requirement_id,
        evidence_type=evidence_type,
        source=observation.component,
        source_event_id=f"agent-observation-{digest}",
        workflow=agent.workflow,
        outcome=outcome,
        observed_at=observation.observed_at,
        ingested_at=observation.observed_at,
        provenance=provenance,
        attributes=(
            EvidenceAttribute(
                key=safe_key,
                value=observation.outcome is ControlOutcome.PASS,
            ),
        ),
    )


def build_safe_canary_evidence(
    *,
    settings: AgentIntegrationSettings,
    agent: AgentDefinition,
    observed_at: datetime,
    outcome: EvidenceOutcome = EvidenceOutcome.PASS,
    event_label: str = "baseline",
) -> EvidenceEnvelope:
    """Create one independent, side-effect-free extraction canary attestation."""

    digest = _stable_digest(
        *agent.scope.storage_key,
        agent.workflow.workflow_id,
        agent.workflow.execution_id,
        agent.workflow.trace_id,
        "invoice-extraction-safe-canary",
        event_label,
        observed_at.isoformat(),
    )
    return EvidenceEnvelope(
        evidence_id=f"safe-canary-{digest}",
        control_id="invoice-extraction-guardrail",
        requirement_id="invoice-extraction-safe-canary",
        evidence_type=EvidenceType.CANARY_RESULT,
        source=CANARY_SOURCE,
        source_event_id=f"safe-canary-event-{digest}",
        workflow=agent.workflow,
        outcome=outcome,
        observed_at=observed_at,
        ingested_at=observed_at,
        provenance=settings.canary_provenance(),
        attributes=(
            EvidenceAttribute(key="synthetic", value=True),
            EvidenceAttribute(key="side_effects_absent", value=True),
            EvidenceAttribute(key="canary_safe", value=True),
        ),
    )


def run_safe_extraction_canary(
    *,
    settings: AgentIntegrationSettings,
    agent: AgentDefinition,
    observed_at: datetime,
    event_label: str = "bootstrap",
) -> EvidenceEnvelope:
    """Probe strict schema rejection with synthetic data and no external effects."""

    malformed_synthetic = {
        "document_id": "synthetic-canary",
        "vendor_name": "Synthetic Vendor",
        "invoice_number": "SYNTHETIC-1",
        "invoice_date": "2026-01-01T00:00:00Z",
        "currency": "USD",
        "line_items": [
            {
                "description": "Synthetic item",
                "quantity": "1",
                "unit_price": "1.00",
                "line_total": "1.00",
            }
        ],
        "subtotal": "1.00",
        "tax": "0.00",
        "total": "999.00",
    }
    try:
        ExtractedInvoice.model_validate(malformed_synthetic)
    except ValidationError:
        outcome = EvidenceOutcome.PASS
    else:
        outcome = EvidenceOutcome.FAIL
    return build_safe_canary_evidence(
        settings=settings,
        agent=agent,
        observed_at=observed_at,
        outcome=outcome,
        event_label=event_label,
    )


def _fail_closed_human_review(
    result: InvoiceWorkflowResult,
    failure_outcome: ToolInvocationOutcome,
) -> InvoiceWorkflowResult:
    """Replace the synthetic continuation with the real typed routing failure."""

    tool_calls = tuple(
        ToolCallRecord(
            tool_name=call.tool_name,
            outcome=failure_outcome,
            detail=None,
        )
        if call.tool_name == "request_human_review"
        else call
        for call in result.tool_calls
    )
    observations = tuple(
        observation.model_copy(
            update={
                "outcome": ControlOutcome.UNAVAILABLE,
                "reason": "Human-review routing was unavailable.",
                "safe_next_action": (
                    "Keep the invoice blocked and retry the human-review connection."
                ),
                "attributes": (),
            }
        )
        if observation.control_key is ControlKey.HITL_BOUNDARY
        else observation
        for observation in result.control_observations
    )
    category = (
        FailureCategory.TIMEOUT
        if failure_outcome is ToolInvocationOutcome.TIMEOUT
        else FailureCategory.TOOL_ERROR
    )
    return result.model_copy(
        update={
            "status": WorkflowStatus.RECONCILIATION_FAILED,
            "final_stage": WorkflowStage.RECONCILIATION,
            "tool_calls": tool_calls,
            "control_observations": observations,
            "human_review_ticket_id": None,
            "reconciliation_failure": AgentFailure(
                category=category,
                message="Human-review routing was unavailable.",
                attempts=1,
                safe_next_action=(
                    "Keep the invoice blocked and retry the human-review connection."
                ),
                document_id=result.document_id,
            ),
        }
    )


def _safe_response(
    result: InvoiceWorkflowResult,
    receipts: tuple[EvidenceReceipt, ...],
    compliance: ComplianceReadModel,
) -> InvoiceRunResponse:
    """Select only fixed, bounded fields from the richer agent result."""

    return InvoiceRunResponse(
        document_id=result.document_id,
        workflow_status=result.status.value,
        final_stage=result.final_stage.value,
        disposition=result.disposition.value if result.disposition is not None else None,
        model_usage=ModelUsageSummary(
            model_calls=result.model_stats.model_calls,
            input_tokens=result.model_stats.input_tokens,
            output_tokens=result.model_stats.output_tokens,
        ),
        tool_calls=tuple(
            SafeToolCallSummary(
                tool_name=call.tool_name,
                outcome=call.outcome.value,
            )
            for call in result.tool_calls
        ),
        evidence=receipts,
        safe_next_action=_safe_action(result),
        compliance=compliance,
    )


def _safe_action(result: InvoiceWorkflowResult) -> str:
    if result.status is WorkflowStatus.EXTRACTION_FAILED:
        return "Route the invoice to a human reviewer; no automated payment action is available."
    if result.status is WorkflowStatus.RECONCILIATION_FAILED:
        return "Inspect the authoritative tool connection and route the invoice to a human reviewer."
    if result.disposition is not None and result.disposition.value == "BLOCK":
        return "Await human review and keep the invoice blocked; no payment action is available."
    if result.disposition is not None and result.disposition.value == "HUMAN_REVIEW":
        return "Await the human decision; no payment action is available."
    return "Continue only to the next deterministic policy stage; this is not payment approval."


def _control(
    *,
    control_id: str,
    display_name: str,
    requirements: tuple[RequiredEvidenceSpecification, ...],
    customer_impact: str,
) -> ControlDefinition:
    return ControlDefinition(
        control_id=control_id,
        display_name=display_name,
        required_evidence=requirements,
        customer_impact=customer_impact,
        next_safe_action=(
            f"Inspect {display_name.lower()}, remediate the control, and emit fresh verified PASS evidence."
        ),
    )


def _requirement(
    agent: AgentDefinition,
    control_id: str,
    requirement_id: str,
) -> RequiredEvidenceSpecification:
    control = next(item for item in agent.controls if item.control_id == control_id)
    return next(
        item for item in control.required_evidence if item.requirement_id == requirement_id
    )


def _stable_digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]
