from __future__ import annotations

from datetime import timedelta

import pytest

from proofloop.agents.model_provider import (
    FakeModelProvider,
    FakeStep,
    ModelProvider,
    ModelTimeoutError,
    NonRetryableModelError,
    RetryableModelError,
    StopReason,
    StructuredGenerationRequest,
)


def _request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        request_id="req-1",
        prompt_id="invoice.extraction",
        prompt_version="1.0.0",
        trusted_instructions="extract fields",
        untrusted_input="some invoice text",
        response_schema_id="ExtractedInvoice",
        max_output_tokens=1000,
        timeout=timedelta(seconds=5),
    )


def test_fake_provider_conforms_to_protocol() -> None:
    provider = FakeModelProvider(steps=[FakeStep(kind="response", raw_output="{}")])
    assert isinstance(provider, ModelProvider)


def test_scripted_success_returns_response_and_counts_call() -> None:
    provider = FakeModelProvider(
        steps=[FakeStep(kind="response", raw_output='{"ok":true}', output_tokens=7)]
    )
    response = provider.generate_structured(_request())
    assert response.raw_output == '{"ok":true}'
    assert response.stop_reason is StopReason.COMPLETED
    assert response.token_usage is not None
    assert response.token_usage.output_tokens == 7
    assert provider.call_count == 1


def test_timeout_step_raises_retryable_timeout_and_counts() -> None:
    provider = FakeModelProvider(steps=[FakeStep(kind="timeout")])
    with pytest.raises(ModelTimeoutError):
        provider.generate_structured(_request())
    assert provider.call_count == 1


def test_retryable_and_nonretryable_steps_raise_expected_types() -> None:
    retry_provider = FakeModelProvider(steps=[FakeStep(kind="retryable")])
    with pytest.raises(RetryableModelError):
        retry_provider.generate_structured(_request())

    fatal_provider = FakeModelProvider(steps=[FakeStep(kind="nonretryable")])
    with pytest.raises(NonRetryableModelError):
        fatal_provider.generate_structured(_request())


def test_steps_are_consumed_in_order_then_last_repeats() -> None:
    provider = FakeModelProvider(
        steps=[
            FakeStep(kind="retryable"),
            FakeStep(kind="response", raw_output='{"n":1}'),
        ]
    )
    with pytest.raises(RetryableModelError):
        provider.generate_structured(_request())
    first = provider.generate_structured(_request())
    second = provider.generate_structured(_request())  # last step repeats
    assert first.raw_output == '{"n":1}'
    assert second.raw_output == '{"n":1}'
    assert provider.call_count == 3
    assert len(provider.requests) == 3
