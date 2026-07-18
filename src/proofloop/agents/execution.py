"""Bounded-execution primitives shared by the agents.

These types enforce the "no hidden model cost" and "no unbounded loop" rules:
every agent runs under an explicit call cap, retry cap, and deadline, and every
failure is a typed, customer-safe category — never an uncaught exception.
"""

from __future__ import annotations

from datetime import timedelta
from enum import Enum

from pydantic import Field, field_validator

from proofloop.agents._base import AgentModel, Identifier


class FailureCategory(str, Enum):
    """Deterministic, customer-safe failure classes."""

    INVALID_OUTPUT = "INVALID_OUTPUT"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    TIMEOUT = "TIMEOUT"
    NON_RETRYABLE_ERROR = "NON_RETRYABLE_ERROR"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    TOOL_ERROR = "TOOL_ERROR"


class ExecutionLimits(AgentModel):
    """Hard caps for one agent invocation.

    `max_model_calls` is an absolute ceiling on structured model calls; the loop
    can never exceed it regardless of `max_retries`.
    """

    max_model_calls: int = Field(default=2, ge=1, le=10)
    max_retries: int = Field(default=1, ge=0, le=9)
    timeout: timedelta = Field(default=timedelta(seconds=30))

    @field_validator("timeout")
    @classmethod
    def timeout_must_be_positive(cls, value: timedelta) -> timedelta:
        if value <= timedelta(0):
            raise ValueError("timeout must be greater than zero")
        return value

    def allowed_attempts(self) -> int:
        """Total structured calls permitted: bounded by both caps."""

        return min(self.max_model_calls, self.max_retries + 1)


class AgentFailure(AgentModel):
    """Typed, explainable failure returned instead of raising to the caller."""

    category: FailureCategory
    message: Identifier
    attempts: int = Field(ge=0)
    safe_next_action: Identifier
    document_id: Identifier | None = None
