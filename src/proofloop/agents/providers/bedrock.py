"""Bedrock Converse / Nova-compatible ModelProvider adapter.

This adapter maps the vendor-neutral ``StructuredGenerationRequest`` onto an
Amazon Bedrock *Converse* call and maps the response — content, token usage,
stop reason — plus throttling, timeout, and non-retryable failures back onto the
existing provider contracts.

Cloud-neutrality is preserved deliberately:

* ``boto3``/``botocore`` are NOT imported here. The Bedrock runtime client is
  injected as a structural ``Protocol``; the agent core never depends on the SDK.
* No model id, region, credential, or account value is hard-coded. The model id
  is supplied through ``BedrockProviderConfig``; region and credentials belong to
  the already-constructed client provided by the composition root.

Nothing in this module performs a real AWS request; a real call happens only
when a caller injects a real client and invokes ``generate_structured``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Mapping, Protocol, runtime_checkable

from proofloop.agents.model_provider import (
    ModelProviderError,
    ModelTimeoutError,
    NonRetryableModelError,
    RetryableModelError,
    StopReason,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TokenUsage,
)


@runtime_checkable
class BedrockRuntimeClient(Protocol):
    """The minimal structural shape of a Bedrock runtime client.

    A real ``boto3.client("bedrock-runtime")`` satisfies this without the agent
    core importing boto3.
    """

    def converse(self, **kwargs: Any) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class BedrockProviderConfig:
    """Injected, non-secret configuration for the adapter.

    ``model_id`` and ``provider_id`` are supplied by the composition root. No
    region, credential, or account value lives here; those belong to the client.
    """

    model_id: str
    provider_id: str = "bedrock-converse"
    additional_model_request_fields: Mapping[str, Any] | None = None
    structured_output_schema: Mapping[str, Any] | None = None
    structured_output_name: str = "structured_response"
    structured_output_description: str = "Validated structured response."


# Bedrock stop reasons -> vendor-neutral stop reasons. Unknown/tool_use reasons
# map to CONTENT_FILTER so the extraction agent treats them as non-completed and
# fails safely rather than trusting a truncated or unexpected result.
_STOP_REASON_MAP: dict[str, StopReason] = {
    "end_turn": StopReason.COMPLETED,
    "stop_sequence": StopReason.COMPLETED,
    "max_tokens": StopReason.MAX_TOKENS,
    "content_filtered": StopReason.CONTENT_FILTER,
    "guardrail_intervened": StopReason.CONTENT_FILTER,
}

# Error codes that are transient and may be retried within the caller's caps.
_THROTTLING_CODES = frozenset(
    {
        "ThrottlingException",
        "ThrottledException",
        "TooManyRequestsException",
        "ServiceQuotaExceededException",
        "ServiceUnavailableException",
        "ModelNotReadyException",
        "InternalServerException",
    }
)
# Error codes / exception names that denote a timeout (retryable-as-timeout).
_TIMEOUT_CODES = frozenset({"ModelTimeoutException"})
_TIMEOUT_EXCEPTION_NAMES = frozenset(
    {"ReadTimeoutError", "ConnectTimeoutError", "ConnectionError"}
)


def _error_code(error: Exception) -> str | None:
    response = getattr(error, "response", None)
    if isinstance(response, Mapping):
        detail = response.get("Error")
        if isinstance(detail, Mapping):
            code = detail.get("Code")
            if isinstance(code, str):
                return code
    return None


def _classify_client_error(error: Exception) -> ModelProviderError:
    """Map a raised client error onto the vendor-neutral error hierarchy.

    Unknown failures default to *non-retryable* so an unrecognized error can
    never drive runaway retries and hidden cost.
    """

    code = _error_code(error)
    name = type(error).__name__
    if code in _TIMEOUT_CODES or name in _TIMEOUT_EXCEPTION_NAMES:
        return ModelTimeoutError(f"Bedrock request timed out: {code or name}")
    if code in _THROTTLING_CODES:
        return RetryableModelError(f"Bedrock request throttled: {code}")
    return NonRetryableModelError(f"Bedrock request failed: {code or name}: {error}")


def _map_stop_reason(raw: object) -> StopReason:
    if isinstance(raw, str):
        return _STOP_REASON_MAP.get(raw, StopReason.CONTENT_FILTER)
    return StopReason.CONTENT_FILTER


@dataclass
class BedrockConverseProvider:
    """A ``ModelProvider`` backed by an injected Bedrock runtime client."""

    client: BedrockRuntimeClient
    config: BedrockProviderConfig
    _last_request_kwargs: dict[str, Any] = field(default_factory=dict, init=False)

    def _build_request(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        # Trusted instructions go into the Converse `system` block; untrusted
        # document text goes into a `user` message. They are never concatenated,
        # so injection text in the invoice cannot become an instruction.
        kwargs: dict[str, Any] = {
            "modelId": self.config.model_id,
            "system": [{"text": request.trusted_instructions}],
            "messages": [
                {"role": "user", "content": [{"text": request.untrusted_input}]}
            ],
            "inferenceConfig": {"maxTokens": request.max_output_tokens},
        }
        if self.config.additional_model_request_fields is not None:
            kwargs["additionalModelRequestFields"] = dict(
                self.config.additional_model_request_fields
            )
        if self.config.structured_output_schema is not None:
            # Converse structured output is a top-level API contract, not an
            # provider-specific additional request field. Canonical JSON makes
            # the exact contract deterministic and easy to regression-test.
            kwargs["outputConfig"] = {
                "textFormat": {
                    "type": "json_schema",
                    "structure": {
                        "jsonSchema": {
                            "name": self.config.structured_output_name,
                            "description": self.config.structured_output_description,
                            "schema": json.dumps(
                                self.config.structured_output_schema,
                                separators=(",", ":"),
                                sort_keys=True,
                            ),
                        }
                    },
                }
            }
        return kwargs

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        kwargs = self._build_request(request)
        self._last_request_kwargs = kwargs
        try:
            raw = self.client.converse(**kwargs)
        except ModelProviderError:
            raise
        except Exception as error:  # noqa: BLE001 - deliberately classified below
            raise _classify_client_error(error) from error

        return self._map_response(request, raw)

    def _map_response(
        self,
        request: StructuredGenerationRequest,
        raw: Mapping[str, Any],
    ) -> StructuredGenerationResponse:
        try:
            content = raw["output"]["message"]["content"]
            text = "".join(
                block["text"] for block in content if isinstance(block.get("text"), str)
            )
            stop_reason = _map_stop_reason(raw.get("stopReason"))
            usage = raw.get("usage")
            token_usage = (
                TokenUsage(
                    input_tokens=int(usage["inputTokens"]),
                    output_tokens=int(usage["outputTokens"]),
                )
                if isinstance(usage, Mapping)
                else None
            )
            metrics = raw.get("metrics")
            latency = (
                timedelta(milliseconds=int(metrics["latencyMs"]))
                if isinstance(metrics, Mapping) and "latencyMs" in metrics
                else None
            )
        except (KeyError, TypeError, ValueError) as error:
            raise NonRetryableModelError(
                f"Bedrock returned a malformed Converse response: {error}"
            ) from error

        return StructuredGenerationResponse(
            request_id=request.request_id,
            provider_id=self.config.provider_id,
            raw_output=text,
            stop_reason=stop_reason,
            token_usage=token_usage,
            latency=latency,
        )
