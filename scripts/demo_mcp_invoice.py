"""ProofLoop's invoice workflow driven through LIVE MCP tools.

This launches the ProofLoop MCP tool server as a **separate subprocess**,
connects an MCP client to it over stdio, and runs the real
``run_invoice_workflow``. Extraction uses an offline fake model (no cloud/API
key), but every reconciliation tool call — purchase order, vendor, duplicate
check, and the human-review escalation — travels over the Model Context Protocol
to the server process and back. The workflow code is unchanged: the MCP client
adapters satisfy its existing tool protocols.

    python scripts/demo_mcp_invoice.py

No cloud, API key, or network access is required.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from proofloop.agents.contracts import (
    ContentType,
    InvoiceInput,
    TrustedInvoiceMetadata,
)
from proofloop.agents.mcp.client import MCPToolClient, default_server_parameters
from proofloop.agents.model_provider import FakeModelProvider, FakeStep
from proofloop.agents.workflow import run_invoice_workflow

UTC = timezone.utc


def _extracted_invoice_json(**overrides: Any) -> str:
    """A well-formed, arithmetic-consistent ExtractedInvoice payload as JSON.

    This is what the fake model 'returns' so extraction succeeds offline. It is
    demo data, not evidence of real extraction accuracy.
    """

    payload: dict[str, Any] = {
        "document_id": "doc-1",
        "vendor_name": "Acme Supplies",
        "vendor_id": "V1",
        "invoice_number": "INV-9",
        "invoice_date": "2026-07-10T00:00:00Z",
        "po_number": "PO-1",
        "currency": "USD",
        "line_items": [
            {
                "description": "Widgets",
                "quantity": "2",
                "unit_price": "50.00",
                "tax": "5.00",
                "line_total": "105.00",
            }
        ],
        "subtotal": "100.00",
        "tax": "5.00",
        "total": "105.00",
        "status": "COMPLETE",
        "model_reported_confidence": 0.95,
    }
    payload.update(overrides)
    return json.dumps(payload)


def _invoice_input(content: str) -> InvoiceInput:
    return InvoiceInput(
        document_id="doc-1",
        content_type=ContentType.TEXT_PLAIN,
        trusted_metadata=TrustedInvoiceMetadata(
            source_system="accounts-payable",
            received_at=datetime(2026, 7, 10, tzinfo=UTC),
        ),
        untrusted_content=content,
    )


def _run_scenario(client: MCPToolClient, *, title: str, extraction_json: str) -> None:
    provider = FakeModelProvider(steps=[FakeStep(kind="response", raw_output=extraction_json)])
    result = run_invoice_workflow(
        invoice=_invoice_input("Invoice from Acme Supplies. Total 105.00 USD."),
        provider=provider,
        purchase_order_tool=client.purchase_order_tool(),
        vendor_tool=client.vendor_tool(),
        duplicate_tool=client.duplicate_tool(),
        human_review_tool=client.human_review_tool(),
    )

    print(f"\n--- {title} ---")
    print(f"status:       {result.status.value}")
    print(f"disposition:  {result.disposition.value if result.disposition else 'n/a'}")
    print("tool calls over MCP:")
    for call in result.tool_calls:
        detail = f" ({call.detail})" if call.detail else ""
        print(f"    - {call.tool_name}: {call.outcome.value}{detail}")
    if result.human_review_ticket_id:
        print(f"human-review ticket: {result.human_review_ticket_id}")
    print("reasons: " + ("; ".join(result.reasons) or "none"))


def main() -> None:
    print("Launching ProofLoop MCP tool server as a subprocess (stdio transport)...")
    with MCPToolClient(default_server_parameters()) as client:
        tools = client.list_tool_names()
        print(f"MCP handshake OK. Tools discovered over the protocol: {tools}")

        # Scenario 1: a clean invoice that matches PO-1 -> ACCEPT.
        # The three read tools are called over MCP.
        _run_scenario(
            client,
            title="Scenario 1: clean invoice (matches PO-1)",
            extraction_json=_extracted_invoice_json(),
        )

        # Scenario 2: no purchase-order number -> HUMAN_REVIEW.
        # This additionally exercises the human-review WRITE tool over MCP.
        _run_scenario(
            client,
            title="Scenario 2: missing purchase order (routes to a human)",
            extraction_json=_extracted_invoice_json(po_number=None),
        )

    print("\nMCP session closed; server subprocess terminated cleanly.")


if __name__ == "__main__":
    main()
