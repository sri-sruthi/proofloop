"""Cloud-neutral model-provider abstraction and a deterministic fake.

The `ModelProvider` protocol is the single replaceable seam for an LLM. It has
no network dependency and never exposes hidden chain-of-thought. A real Bedrock
provider is deliberately NOT implemented in this phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Protocol, Sequence, runtime_checkable

from pydantic import Field

from proofloop.agents._base import AgentModel, Identifier


class StopReason(str, Enum):
    """Why the model stopped producing output."""

    COMPLETED = "COMPLETED"
    MAX_TOKENS = "MAX_TOKENS"
    CONTENT_FILTER = "CONTENT_FILTER"


class ModelProviderError(Exception):
    """Base class for provider failures."""


class RetryableModelError(ModelProviderError):
    """Transient failure (e.g. throttling) that may be retried within limits."""


class NonRetryableModelError(ModelProviderError):
    """Permanent failure (e.g. bad request) that must not be retried."""


class ModelTimeoutError(RetryableModelError):
    """The provider exceeded the request deadline; retryable within limits."""


class TokenUsage(AgentModel):
    """Reported token consumption, for cost attribution ("no hidden cost")."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class StructuredGenerationRequest(AgentModel):
    """A single structured-generation request.

    Trusted instructions and untrusted input are separate fields on purpose: the
    document/tool payload is DATA and must never be concatenated into the
    trusted instruction channel.
    """

    request_id: Identifier
    prompt_id: Identifier
    prompt_version: Identifier
    trusted_instructions: str = Field(min_length=1)
    untrusted_input: str
    response_schema_id: Identifier
    max_output_tokens: int = Field(gt=0, le=100_000)
    timeout: timedelta


class StructuredGenerationResponse(AgentModel):
    """A single structured-generation response. No hidden reasoning is exposed."""

    request_id: Identifier
    provider_id: Identifier
    raw_output: str
    stop_reason: StopReason = StopReason.COMPLETED
    token_usage: TokenUsage | None = None
    latency: timedelta | None = None


@runtime_checkable
class ModelProvider(Protocol):
    """The replaceable model seam. Implementations must not leak vendor types."""

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Return one validated candidate for the caller to schema-check."""


@dataclass
class FakeStep:
    """One scripted behavior for `FakeModelProvider`."""

    kind: str  # "response" | "timeout" | "retryable" | "nonretryable"
    raw_output: str = ""
    stop_reason: StopReason = StopReason.COMPLETED
    input_tokens: int = 0
    output_tokens: int = 0
    provider_id: str = "fake-model-v0"


@dataclass
class FakeModelProvider:
    """Deterministic, offline provider for tests.

    Steps are consumed in order; once exhausted the last step repeats. Every
    call — successful or raising — increments `call_count`, so tests can assert
    the agent never exceeds its call cap.
    """

    steps: Sequence[FakeStep]
    call_count: int = 0
    requests: list[StructuredGenerationRequest] = field(default_factory=list)
    _index: int = 0

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        self.call_count += 1
        self.requests.append(request)
        step = self.steps[min(self._index, len(self.steps) - 1)]
        self._index += 1

        if step.kind == "timeout":
            raise ModelTimeoutError(f"request {request.request_id} timed out")
        if step.kind == "retryable":
            raise RetryableModelError(f"request {request.request_id} throttled")
        if step.kind == "nonretryable":
            raise NonRetryableModelError(f"request {request.request_id} rejected")
        if step.kind != "response":
            raise ValueError(f"unknown FakeStep kind: {step.kind!r}")

        return StructuredGenerationResponse(
            request_id=request.request_id,
            provider_id=step.provider_id,
            raw_output=step.raw_output,
            stop_reason=step.stop_reason,
            token_usage=TokenUsage(
                input_tokens=step.input_tokens,
                output_tokens=step.output_tokens,
            ),
            latency=timedelta(milliseconds=1),
        )
