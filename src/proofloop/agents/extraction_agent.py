"""Bounded invoice extraction agent.

One structured model call per attempt, a hard call cap, retries only for
explicitly retryable failures, and typed safe failure on invalid output. The
agent calls no business tools, executes no policy, and emits no ProofLoop
evidence in this phase.
"""

from __future__ import annotations

from pydantic import ValidationError

from proofloop.agents.contracts import ExtractedInvoice, InvoiceInput
from proofloop.agents.execution import AgentFailure, ExecutionLimits, FailureCategory
from proofloop.agents.model_provider import (
    ModelProvider,
    ModelTimeoutError,
    NonRetryableModelError,
    RetryableModelError,
    StopReason,
    StructuredGenerationRequest,
)
from proofloop.agents.prompts.loader import LoadedPrompt, load_prompt

EXTRACTION_PROMPT_ID = "invoice.extraction"

_REVIEW_ACTION = "Route this invoice to a human reviewer; automated extraction did not produce a trustworthy result."


def run_extraction(
    *,
    invoice: InvoiceInput,
    provider: ModelProvider,
    limits: ExecutionLimits | None = None,
    prompt: LoadedPrompt | None = None,
    max_output_tokens: int = 2_000,
) -> ExtractedInvoice | AgentFailure:
    """Extract structured fields from one invoice.

    Returns a validated `ExtractedInvoice` on success or a typed `AgentFailure`
    on invalid output or exhausted retries. Never raises for model/validation
    problems.
    """

    limits = limits or ExecutionLimits()
    prompt = prompt or load_prompt(EXTRACTION_PROMPT_ID)
    attempts_allowed = limits.allowed_attempts()

    request = StructuredGenerationRequest(
        request_id=f"{invoice.document_id}:extraction",
        prompt_id=prompt.definition.prompt_id,
        prompt_version=prompt.definition.version,
        trusted_instructions=(
            f"{prompt.definition.trusted_instructions}\n\n"
            f"{prompt.definition.output_contract}\n\n"
            f"{prompt.definition.untrusted_data_policy}"
        ),
        untrusted_input=invoice.untrusted_content,
        response_schema_id="ExtractedInvoice",
        max_output_tokens=max_output_tokens,
        timeout=limits.timeout,
    )

    retries_used = 0
    for attempt in range(attempts_allowed):
        can_retry = attempt < attempts_allowed - 1 and retries_used < limits.max_retries
        try:
            response = provider.generate_structured(request)
        except ModelTimeoutError:
            if can_retry:
                retries_used += 1
                continue
            return _fail(
                FailureCategory.TIMEOUT,
                "The extraction model timed out and retries were exhausted.",
                provider,
                invoice,
            )
        except RetryableModelError:
            if can_retry:
                retries_used += 1
                continue
            return _fail(
                FailureCategory.RETRY_EXHAUSTED,
                "The extraction model kept failing transiently; retries exhausted.",
                provider,
                invoice,
            )
        except NonRetryableModelError:
            return _fail(
                FailureCategory.NON_RETRYABLE_ERROR,
                "The extraction model rejected the request permanently.",
                provider,
                invoice,
            )

        if response.stop_reason is not StopReason.COMPLETED:
            return _fail(
                FailureCategory.INVALID_OUTPUT,
                f"The extraction model stopped early: {response.stop_reason.value}.",
                provider,
                invoice,
            )

        try:
            extracted = ExtractedInvoice.model_validate_json(response.raw_output)
        except ValidationError:
            return _fail(
                FailureCategory.INVALID_OUTPUT,
                "The extraction model returned output that failed schema validation.",
                provider,
                invoice,
            )

        if extracted.document_id != invoice.document_id:
            return _fail(
                FailureCategory.INVALID_OUTPUT,
                "The extracted document_id did not match the requested invoice.",
                provider,
                invoice,
            )
        return extracted

    return _fail(
        FailureCategory.RETRY_EXHAUSTED,
        "Extraction did not succeed within the allowed attempts.",
        provider,
        invoice,
    )


def _fail(
    category: FailureCategory,
    message: str,
    provider: ModelProvider,
    invoice: InvoiceInput,
) -> AgentFailure:
    attempts = getattr(provider, "call_count", 0)
    return AgentFailure(
        category=category,
        message=message,
        attempts=attempts,
        safe_next_action=_REVIEW_ACTION,
        document_id=invoice.document_id,
    )
