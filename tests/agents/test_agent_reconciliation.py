from __future__ import annotations

from decimal import Decimal

from agent_fixtures import extracted_invoice, known_vendor, matching_po
from proofloop.agents.contracts import (
    Disposition,
    DuplicateStatus,
    MismatchCategory,
    ReconciliationResult,
)
from proofloop.agents.execution import AgentFailure, FailureCategory
from proofloop.agents.mcp.tool_specs import (
    InMemoryDuplicateCheckTool,
    InMemoryPurchaseOrderTool,
    InMemoryVendorTool,
)
from proofloop.agents.policy import PolicyConfig
from proofloop.agents.reconciliation_agent import run_reconciliation


def _run(
    extraction,
    *,
    po=None,
    vendors=(),
    duplicate=DuplicateStatus.NOT_DUPLICATE,
    config=None,
    po_timeout=False,
):
    po_records = {po.po_number: po} if po is not None else {}
    return run_reconciliation(
        extraction=extraction,
        purchase_order_tool=InMemoryPurchaseOrderTool(po_records, raise_timeout=po_timeout),
        vendor_tool=InMemoryVendorTool(vendors),
        duplicate_tool=InMemoryDuplicateCheckTool(duplicate),
        config=config or PolicyConfig(),
    )


def test_fully_matching_invoice_accepts_for_policy_evaluation() -> None:
    result = _run(extracted_invoice(), po=matching_po(), vendors=(known_vendor(),))
    assert isinstance(result, ReconciliationResult)
    assert result.decision.disposition is Disposition.ACCEPT_FOR_POLICY_EVALUATION
    assert result.findings.matched_facts is not None
    assert result.findings.matched_facts.po_total == Decimal("105.00")


def test_unknown_vendor_blocks() -> None:
    result = _run(extracted_invoice(), po=matching_po(), vendors=())
    assert result.decision.disposition is Disposition.BLOCK
    assert MismatchCategory.UNKNOWN_VENDOR in {
        m.category for m in result.findings.mismatches
    }


def test_missing_po_escalates_by_default() -> None:
    result = _run(
        extracted_invoice(po_number=None), po=None, vendors=(known_vendor(),)
    )
    assert result.decision.disposition is Disposition.HUMAN_REVIEW
    assert MismatchCategory.PO_NOT_FOUND in {
        m.category for m in result.findings.mismatches
    }


def test_missing_po_can_be_configured_to_block() -> None:
    result = _run(
        extracted_invoice(po_number=None),
        po=None,
        vendors=(known_vendor(),),
        config=PolicyConfig(missing_po_disposition=Disposition.BLOCK),
    )
    assert result.decision.disposition is Disposition.BLOCK


def test_confirmed_duplicate_blocks() -> None:
    result = _run(
        extracted_invoice(),
        po=matching_po(),
        vendors=(known_vendor(),),
        duplicate=DuplicateStatus.CONFIRMED_DUPLICATE,
    )
    assert result.decision.disposition is Disposition.BLOCK


def test_amount_mismatch_escalates() -> None:
    result = _run(
        extracted_invoice(),
        po=matching_po(total=Decimal("500.00")),
        vendors=(known_vendor(),),
    )
    assert result.decision.disposition is Disposition.HUMAN_REVIEW
    assert MismatchCategory.AMOUNT_MISMATCH in {
        m.category for m in result.findings.mismatches
    }


def test_model_extracted_values_cannot_override_authoritative_facts() -> None:
    # Extraction (the model's product) claims a different vendor and total than
    # the authoritative PO; matched_facts must reflect the tool record, not the
    # extraction, and the discrepancy is surfaced as a mismatch.
    malicious = extracted_invoice(
        vendor_name="Evil Corp",
        total="9999.00",
        subtotal="9999.00",
        tax="0.00",
        line_items=[
            {
                "description": "Widgets",
                "quantity": "1",
                "unit_price": "9999.00",
                "tax": "0.00",
                "line_total": "9999.00",
            }
        ],
    )
    result = _run(malicious, po=matching_po(), vendors=(known_vendor(),))
    assert isinstance(result, ReconciliationResult)
    assert result.findings.matched_facts is not None
    assert result.findings.matched_facts.vendor_name == "Acme Supplies"
    assert result.findings.matched_facts.po_total == Decimal("105.00")
    assert MismatchCategory.AMOUNT_MISMATCH in {
        m.category for m in result.findings.mismatches
    }


def test_tool_timeout_fails_safely() -> None:
    result = _run(extracted_invoice(), po=matching_po(), vendors=(known_vendor(),), po_timeout=True)
    assert isinstance(result, AgentFailure)
    assert result.category is FailureCategory.TOOL_ERROR
    assert result.document_id == "doc-1"


def test_reconciliation_returns_recommendation_not_payment_approval() -> None:
    result = _run(extracted_invoice(), po=matching_po(), vendors=(known_vendor(),))
    assert isinstance(result, ReconciliationResult)
    # The reachable dispositions are exactly the three deterministic ones; none
    # authorizes payment. On the accept path this is stated explicitly.
    assert result.decision.disposition is Disposition.ACCEPT_FOR_POLICY_EVALUATION
    assert "not payment approval" in result.decision.safe_next_action.lower()
