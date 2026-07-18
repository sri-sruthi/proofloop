"""Cloud-neutral, MCP-ready business tool specifications and in-memory fakes.

These are typed tool *signatures* plus metadata, not an MCP server. Exactly four
read/write business tools exist. There is deliberately NO payment tool, no
generic HTTP tool, no shell tool, and no evidence-emission tool in this phase.
"""

from __future__ import annotations

from datetime import timedelta
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import Field

from proofloop.agents._base import AgentModel, ExactDecimal, Identifier
from proofloop.agents.contracts import DuplicateStatus


class ToolAccess(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class DataSensitivity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolError(Exception):
    """Base class for tool failures."""


class ToolTimeoutError(ToolError):
    """The tool exceeded its expected latency."""


class ToolSpecification(AgentModel):
    """Metadata contract describing one business tool."""

    name: Identifier
    purpose: Identifier
    input_schema: Identifier
    output_schema: Identifier
    access: ToolAccess
    timeout: timedelta
    idempotent: bool
    data_sensitivity: DataSensitivity
    customer_impact: Identifier
    possible_errors: tuple[Identifier, ...] = ()


# --- Typed tool I/O --------------------------------------------------------


class PurchaseOrderQuery(AgentModel):
    po_number: Identifier


class PurchaseOrderRecord(AgentModel):
    po_number: Identifier
    vendor_id: Identifier
    vendor_name: Identifier
    currency: Identifier
    total: ExactDecimal = Field(ge=0)
    status: Identifier


class VendorQuery(AgentModel):
    vendor_id: Identifier | None = None
    vendor_name: Identifier | None = None


class VendorRecord(AgentModel):
    vendor_id: Identifier
    vendor_name: Identifier
    active: bool


class DuplicateQuery(AgentModel):
    vendor_name: Identifier
    invoice_number: Identifier
    total: ExactDecimal = Field(ge=0)


class DuplicateCheckResult(AgentModel):
    status: DuplicateStatus
    matched_invoice_id: Identifier | None = None


class HumanReviewRequest(AgentModel):
    document_id: Identifier
    reason: Identifier
    idempotency_key: Identifier


class HumanReviewTicket(AgentModel):
    ticket_id: Identifier
    document_id: Identifier
    status: Identifier
    idempotency_key: Identifier


# --- Tool protocols --------------------------------------------------------


@runtime_checkable
class PurchaseOrderTool(Protocol):
    def get_purchase_order(
        self, query: PurchaseOrderQuery
    ) -> PurchaseOrderRecord | None: ...


@runtime_checkable
class VendorTool(Protocol):
    def get_vendor_record(self, query: VendorQuery) -> VendorRecord | None: ...


@runtime_checkable
class DuplicateCheckTool(Protocol):
    def check_duplicate_invoice(
        self, query: DuplicateQuery
    ) -> DuplicateCheckResult: ...


@runtime_checkable
class HumanReviewTool(Protocol):
    def request_human_review(self, request: HumanReviewRequest) -> HumanReviewTicket: ...


# --- The approved specification registry -----------------------------------

APPROVED_TOOL_SPECS: tuple[ToolSpecification, ...] = (
    ToolSpecification(
        name="get_purchase_order",
        purpose="Fetch an authoritative purchase-order record by number.",
        input_schema="PurchaseOrderQuery",
        output_schema="PurchaseOrderRecord",
        access=ToolAccess.READ,
        timeout=timedelta(seconds=5),
        idempotent=True,
        data_sensitivity=DataSensitivity.MEDIUM,
        customer_impact="Reads finance records; wrong data could misroute an invoice.",
        possible_errors=("NOT_FOUND", "TIMEOUT"),
    ),
    ToolSpecification(
        name="get_vendor_record",
        purpose="Fetch an authoritative vendor record.",
        input_schema="VendorQuery",
        output_schema="VendorRecord",
        access=ToolAccess.READ,
        timeout=timedelta(seconds=5),
        idempotent=True,
        data_sensitivity=DataSensitivity.MEDIUM,
        customer_impact="Reads vendor master data; wrong data could approve an unknown vendor.",
        possible_errors=("NOT_FOUND", "TIMEOUT"),
    ),
    ToolSpecification(
        name="check_duplicate_invoice",
        purpose="Check whether an invoice looks like a duplicate.",
        input_schema="DuplicateQuery",
        output_schema="DuplicateCheckResult",
        access=ToolAccess.READ,
        timeout=timedelta(seconds=5),
        idempotent=True,
        data_sensitivity=DataSensitivity.MEDIUM,
        customer_impact="Prevents double payment; a miss could allow paying twice.",
        possible_errors=("TIMEOUT",),
    ),
    ToolSpecification(
        name="request_human_review",
        purpose="Open (idempotently) a human-review ticket for an invoice.",
        input_schema="HumanReviewRequest",
        output_schema="HumanReviewTicket",
        access=ToolAccess.WRITE,
        timeout=timedelta(seconds=5),
        idempotent=True,
        data_sensitivity=DataSensitivity.LOW,
        customer_impact="Routes a consequential decision to a human; no money moves.",
        possible_errors=("TIMEOUT",),
    ),
)


# --- Deterministic in-memory fakes for tests -------------------------------


class InMemoryPurchaseOrderTool:
    """Fake PO tool. Optionally raises to simulate timeouts."""

    def __init__(
        self,
        records: dict[str, PurchaseOrderRecord] | None = None,
        *,
        raise_timeout: bool = False,
    ) -> None:
        self._records = records or {}
        self._raise_timeout = raise_timeout

    def get_purchase_order(
        self, query: PurchaseOrderQuery
    ) -> PurchaseOrderRecord | None:
        if self._raise_timeout:
            raise ToolTimeoutError("get_purchase_order timed out")
        return self._records.get(query.po_number)


class InMemoryVendorTool:
    """Fake vendor tool keyed by vendor_id and vendor_name."""

    def __init__(
        self,
        records: tuple[VendorRecord, ...] = (),
        *,
        raise_timeout: bool = False,
    ) -> None:
        self._by_id = {r.vendor_id: r for r in records}
        self._by_name = {r.vendor_name: r for r in records}
        self._raise_timeout = raise_timeout

    def get_vendor_record(self, query: VendorQuery) -> VendorRecord | None:
        if self._raise_timeout:
            raise ToolTimeoutError("get_vendor_record timed out")
        if query.vendor_id is not None and query.vendor_id in self._by_id:
            return self._by_id[query.vendor_id]
        if query.vendor_name is not None:
            return self._by_name.get(query.vendor_name)
        return None


class InMemoryDuplicateCheckTool:
    """Fake duplicate tool returning a scripted status."""

    def __init__(
        self,
        status: DuplicateStatus = DuplicateStatus.NOT_DUPLICATE,
        *,
        matched_invoice_id: str | None = None,
        raise_timeout: bool = False,
    ) -> None:
        self._status = status
        self._matched_invoice_id = matched_invoice_id
        self._raise_timeout = raise_timeout

    def check_duplicate_invoice(self, query: DuplicateQuery) -> DuplicateCheckResult:
        if self._raise_timeout:
            raise ToolTimeoutError("check_duplicate_invoice timed out")
        return DuplicateCheckResult(
            status=self._status,
            matched_invoice_id=self._matched_invoice_id,
        )


class InMemoryHumanReviewTool:
    """Fake, idempotent human-review tool keyed by idempotency_key."""

    def __init__(self) -> None:
        self._tickets: dict[str, HumanReviewTicket] = {}
        self.write_count = 0

    def request_human_review(self, request: HumanReviewRequest) -> HumanReviewTicket:
        existing = self._tickets.get(request.idempotency_key)
        if existing is not None:
            return existing
        self.write_count += 1
        ticket = HumanReviewTicket(
            ticket_id=f"ticket-{request.idempotency_key}",
            document_id=request.document_id,
            status="OPEN",
            idempotency_key=request.idempotency_key,
        )
        self._tickets[request.idempotency_key] = ticket
        return ticket
