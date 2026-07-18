"""Stable, customer-safe application errors."""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    BOUNDARY_MISMATCH = "BOUNDARY_MISMATCH"
    WORKFLOW_MISMATCH = "WORKFLOW_MISMATCH"
    EVIDENCE_NOT_DECLARED = "EVIDENCE_NOT_DECLARED"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    UNSAFE_EVIDENCE_PAYLOAD = "UNSAFE_EVIDENCE_PAYLOAD"
    UNSAFE_CANARY_EVIDENCE = "UNSAFE_CANARY_EVIDENCE"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHENTICATION_NOT_CONFIGURED = "AUTHENTICATION_NOT_CONFIGURED"
    INTEGRATION_NOT_CONFIGURED = "INTEGRATION_NOT_CONFIGURED"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApplicationError(Exception):
    """An expected failure safe to expose through an adapter."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
