"""End-to-end tests for the live MCP tool integration.

Two levels of proof:

* ``test_server_exposes_four_tools_over_in_memory_mcp`` uses the SDK's in-memory
  transport for a fast, deterministic protocol round-trip (tool discovery +
  call) with no subprocess.
* ``test_workflow_runs_through_mcp_stdio`` launches the tool server as a real
  subprocess and runs the full ``run_invoice_workflow`` through it over stdio,
  proving the synchronous workflow drives live MCP tools unchanged.
"""

from __future__ import annotations

import asyncio

from agent_fixtures import invoice_input, valid_invoice_json

from mcp import Client

from proofloop.agents.contracts import Disposition
from proofloop.agents.mcp.client import MCPToolClient, default_server_parameters
from proofloop.agents.mcp.server import EXPOSED_TOOL_NAMES, build_server
from proofloop.agents.model_provider import FakeModelProvider, FakeStep
from proofloop.agents.workflow import run_invoice_workflow


def test_server_exposes_four_tools_over_in_memory_mcp() -> None:
    async def scenario() -> None:
        async with Client(build_server()) as client:
            listing = await client.list_tools()
            assert {tool.name for tool in listing.tools} == set(EXPOSED_TOOL_NAMES)

            found = await client.call_tool("get_purchase_order", {"po_number": "PO-1"})
            assert found.is_error is False
            text = next(getattr(b, "text", None) for b in found.content)
            assert '"po_number": "PO-1"' in text
            assert '"total": "105.00"' in text  # exact decimal preserved as string

            missing = await client.call_tool(
                "get_purchase_order", {"po_number": "PO-404"}
            )
            missing_text = next(getattr(b, "text", None) for b in missing.content)
            assert '"record": null' in missing_text

    asyncio.run(scenario())


def _run_workflow_through_mcp(client: MCPToolClient, extraction_json: str):
    provider = FakeModelProvider(
        steps=[FakeStep(kind="response", raw_output=extraction_json)]
    )
    return run_invoice_workflow(
        invoice=invoice_input(),
        provider=provider,
        purchase_order_tool=client.purchase_order_tool(),
        vendor_tool=client.vendor_tool(),
        duplicate_tool=client.duplicate_tool(),
        human_review_tool=client.human_review_tool(),
    )


def test_workflow_runs_through_mcp_stdio() -> None:
    with MCPToolClient(default_server_parameters()) as client:
        assert set(client.list_tool_names()) == set(EXPOSED_TOOL_NAMES)

        # Clean invoice -> ACCEPT; the three read tools resolve over MCP.
        clean = _run_workflow_through_mcp(client, valid_invoice_json())
        assert clean.disposition is Disposition.ACCEPT_FOR_POLICY_EVALUATION
        called = {call.tool_name for call in clean.tool_calls}
        assert {"get_purchase_order", "get_vendor_record", "check_duplicate_invoice"} <= called

        # No purchase order -> HUMAN_REVIEW; the write tool escalates over MCP.
        escalated = _run_workflow_through_mcp(
            client, valid_invoice_json(po_number=None)
        )
        assert escalated.disposition is Disposition.HUMAN_REVIEW
        assert escalated.human_review_ticket_id is not None
        assert "request_human_review" in {
            call.tool_name for call in escalated.tool_calls
        }
