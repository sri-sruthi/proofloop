from __future__ import annotations

from decimal import Decimal

import pytest

from proofloop.agents.contracts import DuplicateStatus
from proofloop.agents.mcp import tool_specs
from proofloop.agents.mcp.tool_specs import (
    APPROVED_TOOL_SPECS,
    DuplicateQuery,
    HumanReviewRequest,
    InMemoryDuplicateCheckTool,
    InMemoryHumanReviewTool,
    InMemoryPurchaseOrderTool,
    InMemoryVendorTool,
    PurchaseOrderQuery,
    ToolAccess,
    ToolTimeoutError,
    VendorQuery,
)
from agent_fixtures import known_vendor, matching_po

APPROVED_NAMES = {spec.name for spec in APPROVED_TOOL_SPECS}


def test_exactly_four_approved_business_tools() -> None:
    assert APPROVED_NAMES == {
        "get_purchase_order",
        "get_vendor_record",
        "check_duplicate_invoice",
        "request_human_review",
    }


def test_no_payment_http_shell_or_evidence_tool_exists() -> None:
    forbidden = ("pay", "payment", "http", "shell", "exec", "evidence", "transfer")
    for name in APPROVED_NAMES:
        assert not any(bad in name.lower() for bad in forbidden)
    # And no such symbol is exported from the tool module.
    exported = dir(tool_specs)
    assert not any("Payment" in symbol for symbol in exported)
    assert not any("Http" in symbol for symbol in exported)


def test_only_human_review_is_a_write_tool() -> None:
    writes = {s.name for s in APPROVED_TOOL_SPECS if s.access is ToolAccess.WRITE}
    assert writes == {"request_human_review"}


def test_purchase_order_lookup_returns_typed_record_or_none() -> None:
    tool = InMemoryPurchaseOrderTool({"PO-1": matching_po()})
    found = tool.get_purchase_order(PurchaseOrderQuery(po_number="PO-1"))
    assert found is not None
    assert found.po_number == "PO-1"
    assert tool.get_purchase_order(PurchaseOrderQuery(po_number="PO-404")) is None


def test_vendor_lookup_by_id_and_name() -> None:
    tool = InMemoryVendorTool((known_vendor(),))
    by_id = tool.get_vendor_record(VendorQuery(vendor_id="V1"))
    assert by_id is not None
    assert by_id.active is True
    by_name = tool.get_vendor_record(VendorQuery(vendor_name="Acme Supplies"))
    assert by_name is not None
    assert by_name.vendor_id == "V1"
    assert tool.get_vendor_record(VendorQuery(vendor_id="V9")) is None


def test_duplicate_tool_returns_scripted_status() -> None:
    tool = InMemoryDuplicateCheckTool(DuplicateStatus.CONFIRMED_DUPLICATE)
    result = tool.check_duplicate_invoice(
        DuplicateQuery(vendor_name="Acme", invoice_number="INV-9", total=Decimal("1"))
    )
    assert result.status is DuplicateStatus.CONFIRMED_DUPLICATE


def test_tool_timeout_is_raised_for_error_handling() -> None:
    tool = InMemoryPurchaseOrderTool({}, raise_timeout=True)
    with pytest.raises(ToolTimeoutError):
        tool.get_purchase_order(PurchaseOrderQuery(po_number="PO-1"))


def test_human_review_request_is_idempotent() -> None:
    tool = InMemoryHumanReviewTool()
    request = HumanReviewRequest(
        document_id="doc-1", reason="low confidence", idempotency_key="doc-1:v1"
    )
    first = tool.request_human_review(request)
    second = tool.request_human_review(request)
    assert first.ticket_id == second.ticket_id
    assert tool.write_count == 1  # a repeat call performs no second write
