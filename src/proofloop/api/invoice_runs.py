"""Cloud-neutral API contracts for one transient invoice workflow run."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from proofloop.application.models import AgentScope, ComplianceReadModel


_OPAQUE_REFERENCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,127}$"
_SSN_SHAPED_REFERENCE = re.compile(r"^\d{3}-\d{2}-\d{4}$")


class InvoiceRunModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class InvoiceContentType(str, Enum):
    TEXT_PLAIN = "TEXT_PLAIN"
    TEXT_OCR = "TEXT_OCR"
    JSON_FIXTURE = "JSON_FIXTURE"


class InvoiceRunRequest(InvoiceRunModel):
    """Bounded request whose invoice content is transient and never persisted."""

    document_id: str = Field(pattern=_OPAQUE_REFERENCE_PATTERN)
    content_type: InvoiceContentType
    source_system: str = Field(min_length=1, max_length=128)
    received_at: datetime
    declared_vendor_hint: str | None = Field(default=None, min_length=1, max_length=128)
    invoice_content: str = Field(min_length=1, max_length=100_000)

    @field_validator("received_at")
    @classmethod
    def received_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("received_at must be UTC-aware")
        return value

    @field_validator("document_id")
    @classmethod
    def document_id_must_be_opaque(cls, value: str) -> str:
        if value.isdigit() or _SSN_SHAPED_REFERENCE.fullmatch(value):
            raise ValueError("document_id must be an opaque reference, not raw data")
        return value


class ModelUsageSummary(InvoiceRunModel):
    model_calls: int = Field(ge=0, le=10)
    input_tokens: int = Field(ge=0, le=1_000_000)
    output_tokens: int = Field(ge=0, le=1_000_000)


class SafeToolCallSummary(InvoiceRunModel):
    tool_name: str = Field(pattern=_OPAQUE_REFERENCE_PATTERN)
    outcome: str = Field(pattern=r"^(OK|EMPTY|TIMEOUT|ERROR)$")


class EvidenceReceipt(InvoiceRunModel):
    control_id: str = Field(pattern=_OPAQUE_REFERENCE_PATTERN)
    requirement_id: str = Field(pattern=_OPAQUE_REFERENCE_PATTERN)
    evidence_id: str = Field(pattern=_OPAQUE_REFERENCE_PATTERN)
    ingest_status: str = Field(pattern=r"^(ACCEPTED|DUPLICATE)$")


class InvoiceRunResponse(InvoiceRunModel):
    """PII-free workflow summary safe for API and Lambda serialization."""

    document_id: str = Field(pattern=_OPAQUE_REFERENCE_PATTERN)
    workflow_status: str = Field(
        pattern=r"^(COMPLETED|EXTRACTION_FAILED|RECONCILIATION_FAILED)$"
    )
    final_stage: str = Field(pattern=r"^(EXTRACTION|RECONCILIATION|COMPLETE)$")
    disposition: str | None = Field(
        default=None,
        pattern=r"^(ACCEPT_FOR_POLICY_EVALUATION|HUMAN_REVIEW|BLOCK)$",
    )
    model_usage: ModelUsageSummary
    tool_calls: tuple[SafeToolCallSummary, ...] = Field(max_length=8)
    evidence: tuple[EvidenceReceipt, ...] = Field(max_length=8)
    safe_next_action: str = Field(min_length=1, max_length=512)
    compliance: ComplianceReadModel


@runtime_checkable
class InvoiceRunPort(Protocol):
    """Injected outer-boundary use case; API imports no agent implementation."""

    def run_invoice(
        self,
        scope: AgentScope,
        request: InvoiceRunRequest,
    ) -> InvoiceRunResponse: ...
