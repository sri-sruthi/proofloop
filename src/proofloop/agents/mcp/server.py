"""A live Model Context Protocol (MCP) server for ProofLoop's invoice tools.

``tool_specs`` defines the four approved business tools as typed *signatures*
plus in-memory backends. This module turns those signatures into a real MCP
server: the same deterministic backends the tests use are now reachable over the
MCP wire protocol (JSON-RPC), so any MCP client — including ProofLoop's own
reconciliation workflow (see ``client.py``) — can call them exactly as a remote
agent tool would.

Exactly four tools are exposed, matching ``APPROVED_TOOL_SPECS``. There is
deliberately NO payment tool, no generic HTTP tool, and no shell tool. Money
never moves; the most consequential action is opening a human-review ticket.

Run it standalone (it speaks MCP over stdin/stdout):

    python -m proofloop.agents.mcp.server
"""

from __future__ import annotations

from decimal import Decimal

from mcp.server.mcpserver import MCPServer

from proofloop.agents.contracts import DuplicateStatus
from proofloop.agents.mcp.tool_specs import (
    DuplicateQuery,
    HumanReviewRequest,
    InMemoryDuplicateCheckTool,
    InMemoryHumanReviewTool,
    InMemoryPurchaseOrderTool,
    InMemoryVendorTool,
    PurchaseOrderQuery,
    PurchaseOrderRecord,
    VendorQuery,
    VendorRecord,
)

SERVER_NAME = "proofloop-invoice-tools"
SERVER_VERSION = "1.0.0"

# Public list of the tool names this server exposes, so clients/tests can assert
# the surface without hard-coding strings in several places.
EXPOSED_TOOL_NAMES: tuple[str, ...] = (
    "get_purchase_order",
    "get_vendor_record",
    "check_duplicate_invoice",
    "request_human_review",
)


def _seed_backends() -> tuple[
    InMemoryPurchaseOrderTool,
    InMemoryVendorTool,
    InMemoryDuplicateCheckTool,
    InMemoryHumanReviewTool,
]:
    """Seed the same deterministic demo data the unit fixtures use.

    One approved vendor (V1 / Acme Supplies) and one open purchase order (PO-1,
    105.00 USD). The duplicate check reports NOT_DUPLICATE. This is demo data,
    not a claim about any real finance system.
    """

    purchase_orders = InMemoryPurchaseOrderTool(
        {
            "PO-1": PurchaseOrderRecord(
                po_number="PO-1",
                vendor_id="V1",
                vendor_name="Acme Supplies",
                currency="USD",
                total=Decimal("105.00"),
                status="OPEN",
            )
        }
    )
    vendors = InMemoryVendorTool(
        (VendorRecord(vendor_id="V1", vendor_name="Acme Supplies", active=True),)
    )
    duplicates = InMemoryDuplicateCheckTool(DuplicateStatus.NOT_DUPLICATE)
    human_review = InMemoryHumanReviewTool()
    return purchase_orders, vendors, duplicates, human_review


def build_server() -> MCPServer:
    """Construct an MCP server with the four approved invoice tools registered.

    The tool functions are thin adapters: they parse the JSON-RPC arguments into
    the same typed query models the workflow uses, call the deterministic
    backend, and return a JSON-serializable dict. Money/quantity fields cross the
    wire as strings so exact decimals are never corrupted by binary floats.
    """

    purchase_orders, vendors, duplicates, human_review = _seed_backends()

    server = MCPServer(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=(
            "Read-only invoice reconciliation tools (purchase order, vendor, "
            "duplicate check) plus one idempotent human-review escalation. "
            "There is deliberately no payment tool."
        ),
    )

    @server.tool(
        description="Fetch an authoritative purchase-order record by number."
    )
    def get_purchase_order(po_number: str) -> dict:
        record = purchase_orders.get_purchase_order(
            PurchaseOrderQuery(po_number=po_number)
        )
        return {"record": record.model_dump(mode="json") if record else None}

    @server.tool(
        description="Fetch an authoritative vendor record by id or name."
    )
    def get_vendor_record(
        vendor_id: str | None = None, vendor_name: str | None = None
    ) -> dict:
        record = vendors.get_vendor_record(
            VendorQuery(vendor_id=vendor_id, vendor_name=vendor_name)
        )
        return {"record": record.model_dump(mode="json") if record else None}

    @server.tool(
        description="Check whether an invoice looks like a duplicate."
    )
    def check_duplicate_invoice(
        vendor_name: str, invoice_number: str, total: str
    ) -> dict:
        result = duplicates.check_duplicate_invoice(
            DuplicateQuery(
                vendor_name=vendor_name,
                invoice_number=invoice_number,
                total=total,
            )
        )
        return result.model_dump(mode="json")

    @server.tool(
        description=(
            "Open (idempotently) a human-review ticket for an invoice. "
            "No money moves; this routes a consequential decision to a human."
        )
    )
    def request_human_review(
        document_id: str, reason: str, idempotency_key: str
    ) -> dict:
        ticket = human_review.request_human_review(
            HumanReviewRequest(
                document_id=document_id,
                reason=reason,
                idempotency_key=idempotency_key,
            )
        )
        return ticket.model_dump(mode="json")

    return server


def main() -> None:
    """Run the server over stdio (the transport MCP hosts launch subprocesses with)."""

    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
