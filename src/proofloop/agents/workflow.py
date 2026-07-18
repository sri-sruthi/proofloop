"""Bounded invoice workflow orchestrator.

Runs extraction, then reconciliation, then routes uncertain/unsafe states to a
human — while preserving the distinct authority of each agent and never
approving or paying an invoice. The orchestrator adds no new model calls of its
own; extraction remains the single bounded model step, reconciliation stays
deterministic, and routing is one idempotent tool write.

The result is a strict, immutable record carrying everything a later evidence
emitter needs: attempt count, provider id, prompt id/version/content-hash, token
usage, start/end UTC timestamps, the final policy disposition, per-tool
outcomes, guardrail control observations, and any typed failure. It constructs no
ProofLoop evidence object — that mapping happens later in a composition root.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from pydantic import Field, field_validator

from proofloop.agents._base import AgentModel, Identifier, require_utc
from proofloop.agents.contracts import (
    Disposition,
    InvoiceInput,
)
from proofloop.agents.execution import AgentFailure, ExecutionLimits
from proofloop.agents.extraction_agent import EXTRACTION_PROMPT_ID, run_extraction
from proofloop.agents.guardrails import ControlObservation, GuardrailMiddleware
from proofloop.agents.mcp.tool_specs import (
    DuplicateCheckResult,
    DuplicateCheckTool,
    DuplicateQuery,
    HumanReviewRequest,
    HumanReviewTicket,
    HumanReviewTool,
    PurchaseOrderQuery,
    PurchaseOrderRecord,
    PurchaseOrderTool,
    ToolError,
    ToolTimeoutError,
    VendorQuery,
    VendorRecord,
    VendorTool,
)
from proofloop.agents.model_provider import (
    ModelProvider,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from proofloop.agents.policy import PolicyConfig
from proofloop.agents.prompts.loader import LoadedPrompt, load_prompt
from proofloop.agents.reconciliation_agent import run_reconciliation


class WorkflowStatus(str, Enum):
    """Terminal status of one workflow run."""

    COMPLETED = "COMPLETED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"


class WorkflowStage(str, Enum):
    """The furthest stage a run reached."""

    EXTRACTION = "EXTRACTION"
    RECONCILIATION = "RECONCILIATION"
    COMPLETE = "COMPLETE"


class ToolInvocationOutcome(str, Enum):
    """Deterministic outcome of one tool call, for audit and evidence."""

    OK = "OK"
    EMPTY = "EMPTY"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class ToolCallRecord(AgentModel):
    """One recorded tool invocation."""

    tool_name: Identifier
    outcome: ToolInvocationOutcome
    detail: Identifier | None = None


class ModelCallStats(AgentModel):
    """Bounded model consumption for cost attribution ("no hidden cost")."""

    provider_id: Identifier | None = None
    model_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class PromptBinding(AgentModel):
    """The exact prompt version used, for provenance."""

    prompt_id: Identifier
    version: Identifier
    content_hash: Identifier


class InvoiceWorkflowResult(AgentModel):
    """Immutable, fully-typed record of one invoice workflow run."""

    document_id: Identifier
    status: WorkflowStatus
    final_stage: WorkflowStage
    disposition: Disposition | None = None
    started_at: datetime
    completed_at: datetime
    prompt_binding: PromptBinding
    model_stats: ModelCallStats
    tool_calls: tuple[ToolCallRecord, ...] = ()
    control_observations: tuple[ControlObservation, ...] = ()
    reasons: tuple[Identifier, ...] = ()
    human_review_ticket_id: Identifier | None = None
    extraction_failure: AgentFailure | None = None
    reconciliation_failure: AgentFailure | None = None
    safe_next_action: Identifier

    _started_is_utc = field_validator("started_at")(require_utc)
    _completed_is_utc = field_validator("completed_at")(require_utc)


# --- Recording wrappers (do not alter agent behavior) ----------------------


@dataclass
class _RecordingModelProvider:
    """Wraps a provider to capture call count and token usage.

    Increments ``call_count`` before delegating (so a raising call is still
    counted, matching the caller's cap accounting) and records only successful
    responses' token usage.
    """

    inner: ModelProvider
    call_count: int = 0
    responses: list[StructuredGenerationResponse] = field(default_factory=list)

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        self.call_count += 1
        response = self.inner.generate_structured(request)
        self.responses.append(response)
        return response


@dataclass
class _ToolRecorder:
    calls: list[ToolCallRecord] = field(default_factory=list)

    def record(
        self,
        tool_name: str,
        outcome: ToolInvocationOutcome,
        detail: str | None = None,
    ) -> None:
        self.calls.append(
            ToolCallRecord(tool_name=tool_name, outcome=outcome, detail=detail)
        )


@dataclass
class _RecordingPurchaseOrderTool:
    inner: PurchaseOrderTool
    recorder: _ToolRecorder

    def get_purchase_order(
        self, query: PurchaseOrderQuery
    ) -> PurchaseOrderRecord | None:
        try:
            result = self.inner.get_purchase_order(query)
        except ToolTimeoutError as error:
            self.recorder.record("get_purchase_order", ToolInvocationOutcome.TIMEOUT, str(error))
            raise
        except ToolError as error:
            self.recorder.record("get_purchase_order", ToolInvocationOutcome.ERROR, str(error))
            raise
        outcome = ToolInvocationOutcome.OK if result is not None else ToolInvocationOutcome.EMPTY
        self.recorder.record("get_purchase_order", outcome)
        return result


@dataclass
class _RecordingVendorTool:
    inner: VendorTool
    recorder: _ToolRecorder

    def get_vendor_record(self, query: VendorQuery) -> VendorRecord | None:
        try:
            result = self.inner.get_vendor_record(query)
        except ToolTimeoutError as error:
            self.recorder.record("get_vendor_record", ToolInvocationOutcome.TIMEOUT, str(error))
            raise
        except ToolError as error:
            self.recorder.record("get_vendor_record", ToolInvocationOutcome.ERROR, str(error))
            raise
        outcome = ToolInvocationOutcome.OK if result is not None else ToolInvocationOutcome.EMPTY
        self.recorder.record("get_vendor_record", outcome)
        return result


@dataclass
class _RecordingDuplicateCheckTool:
    inner: DuplicateCheckTool
    recorder: _ToolRecorder

    def check_duplicate_invoice(self, query: DuplicateQuery) -> DuplicateCheckResult:
        try:
            result = self.inner.check_duplicate_invoice(query)
        except ToolTimeoutError as error:
            self.recorder.record("check_duplicate_invoice", ToolInvocationOutcome.TIMEOUT, str(error))
            raise
        except ToolError as error:
            self.recorder.record("check_duplicate_invoice", ToolInvocationOutcome.ERROR, str(error))
            raise
        self.recorder.record(
            "check_duplicate_invoice", ToolInvocationOutcome.OK, result.status.value
        )
        return result


def _model_stats(recorder: _RecordingModelProvider) -> ModelCallStats:
    provider_id: str | None = None
    input_tokens = 0
    output_tokens = 0
    for response in recorder.responses:
        provider_id = response.provider_id
        if response.token_usage is not None:
            input_tokens += response.token_usage.input_tokens
            output_tokens += response.token_usage.output_tokens
    return ModelCallStats(
        provider_id=provider_id,
        model_calls=recorder.call_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def run_invoice_workflow(
    *,
    invoice: InvoiceInput,
    provider: ModelProvider,
    purchase_order_tool: PurchaseOrderTool,
    vendor_tool: VendorTool,
    duplicate_tool: DuplicateCheckTool,
    human_review_tool: HumanReviewTool,
    limits: ExecutionLimits | None = None,
    config: PolicyConfig | None = None,
    prompt: LoadedPrompt | None = None,
    guardrail: GuardrailMiddleware | None = None,
    now: Callable[[], datetime] | None = None,
) -> InvoiceWorkflowResult:
    """Run the bounded extraction -> reconciliation -> human-routing workflow.

    Stops immediately on extraction failure. Routes ``HUMAN_REVIEW`` and
    ``BLOCK`` dispositions to an idempotent human-review ticket. Never reaches a
    payment action; the model never chooses the disposition.
    """

    limits = limits or ExecutionLimits()
    config = config or PolicyConfig()
    guardrail = guardrail or GuardrailMiddleware()
    clock = now or _default_clock
    loaded_prompt = prompt or load_prompt(EXTRACTION_PROMPT_ID)

    started_at = clock()
    binding = PromptBinding(
        prompt_id=loaded_prompt.definition.prompt_id,
        version=loaded_prompt.definition.version,
        content_hash=loaded_prompt.content_hash,
    )
    observations: list[ControlObservation] = []

    # 1. PII redaction guardrail runs on untrusted content before any model call.
    pii_observation, redaction = guardrail.observe_pii_redaction(
        invoice=invoice, now=clock()
    )
    observations.append(pii_observation)

    # Build a NEW, immutable InvoiceInput carrying only the redacted content.
    # The original invoice is never mutated; the raw PII it holds must never
    # reach the model provider's untrusted_input.
    sanitized_invoice = InvoiceInput(
        document_id=invoice.document_id,
        content_type=invoice.content_type,
        trusted_metadata=invoice.trusted_metadata,
        untrusted_content=redaction.redacted_text,
    )

    # 2. Bounded extraction (the single model step) — on the sanitized input.
    recording_provider = _RecordingModelProvider(provider)
    extraction = run_extraction(
        invoice=sanitized_invoice,
        provider=recording_provider,
        limits=limits,
        prompt=loaded_prompt,
    )
    model_stats = _model_stats(recording_provider)

    if isinstance(extraction, AgentFailure):
        observations.append(
            guardrail.observe_extraction_schema_validation(
                validated=False, detail=extraction.message, now=clock()
            )
        )
        observations.append(
            guardrail.observe_audit_logging(
                document_id=invoice.document_id,
                action="extraction_failed",
                now=clock(),
            )
        )
        return InvoiceWorkflowResult(
            document_id=invoice.document_id,
            status=WorkflowStatus.EXTRACTION_FAILED,
            final_stage=WorkflowStage.EXTRACTION,
            disposition=None,
            started_at=started_at,
            completed_at=clock(),
            prompt_binding=binding,
            model_stats=model_stats,
            control_observations=tuple(observations),
            extraction_failure=extraction,
            safe_next_action=extraction.safe_next_action,
        )

    observations.append(
        guardrail.observe_extraction_schema_validation(
            validated=True,
            detail="Model output validated to the strict ExtractedInvoice schema.",
            now=clock(),
        )
    )

    # 3. Deterministic reconciliation with per-tool outcome recording.
    recorder = _ToolRecorder()
    reconciliation = run_reconciliation(
        extraction=extraction,
        purchase_order_tool=_RecordingPurchaseOrderTool(purchase_order_tool, recorder),
        vendor_tool=_RecordingVendorTool(vendor_tool, recorder),
        duplicate_tool=_RecordingDuplicateCheckTool(duplicate_tool, recorder),
        config=config,
    )

    if isinstance(reconciliation, AgentFailure):
        observations.append(
            guardrail.observe_audit_logging(
                document_id=invoice.document_id,
                action="reconciliation_failed",
                now=clock(),
            )
        )
        return InvoiceWorkflowResult(
            document_id=invoice.document_id,
            status=WorkflowStatus.RECONCILIATION_FAILED,
            final_stage=WorkflowStage.RECONCILIATION,
            disposition=None,
            started_at=started_at,
            completed_at=clock(),
            prompt_binding=binding,
            model_stats=model_stats,
            tool_calls=tuple(recorder.calls),
            control_observations=tuple(observations),
            reconciliation_failure=reconciliation,
            safe_next_action=reconciliation.safe_next_action,
        )

    decision = reconciliation.decision
    disposition = decision.disposition

    # 4. Route uncertain/unsafe states to an idempotent human-review ticket.
    ticket_id: str | None = None
    needs_human = disposition in (Disposition.HUMAN_REVIEW, Disposition.BLOCK)
    if needs_human:
        recording_human = _RecordingHumanReviewTool(human_review_tool, recorder)
        ticket = recording_human.request_human_review(
            HumanReviewRequest(
                document_id=invoice.document_id,
                reason="; ".join(decision.reasons) or disposition.value,
                idempotency_key=f"{invoice.document_id}:{disposition.value}",
            )
        )
        ticket_id = ticket.ticket_id

    observations.append(
        guardrail.observe_hitl_boundary(
            disposition=disposition,
            routed_to_human=needs_human and ticket_id is not None,
            now=clock(),
        )
    )
    observations.append(
        guardrail.observe_audit_logging(
            document_id=invoice.document_id,
            action=f"disposition_{disposition.value}",
            now=clock(),
        )
    )

    return InvoiceWorkflowResult(
        document_id=invoice.document_id,
        status=WorkflowStatus.COMPLETED,
        final_stage=WorkflowStage.COMPLETE,
        disposition=disposition,
        started_at=started_at,
        completed_at=clock(),
        prompt_binding=binding,
        model_stats=model_stats,
        tool_calls=tuple(recorder.calls),
        control_observations=tuple(observations),
        reasons=decision.reasons,
        human_review_ticket_id=ticket_id,
        safe_next_action=decision.safe_next_action,
    )


@dataclass
class _RecordingHumanReviewTool:
    inner: HumanReviewTool
    recorder: _ToolRecorder

    def request_human_review(self, request: HumanReviewRequest) -> HumanReviewTicket:
        try:
            ticket = self.inner.request_human_review(request)
        except ToolTimeoutError as error:
            self.recorder.record("request_human_review", ToolInvocationOutcome.TIMEOUT, str(error))
            raise
        except ToolError as error:
            self.recorder.record("request_human_review", ToolInvocationOutcome.ERROR, str(error))
            raise
        self.recorder.record("request_human_review", ToolInvocationOutcome.OK, ticket.status)
        return ticket
