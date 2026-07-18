"""Bounded, deterministic invoice reconciliation agent.

The agent gathers authoritative facts through the four approved read tools,
treats all tool output as untrusted data, computes typed mismatches, and defers
the disposition to the deterministic `evaluate_policy` function. It performs no
model call in this phase (the reconciliation prompt is reserved), invents no
authoritative facts, and can reach no payment action.
"""

from __future__ import annotations

from proofloop.agents.contracts import (
    ExtractedInvoice,
    MatchedFacts,
    Mismatch,
    MismatchCategory,
    ReconciliationFindings,
    ReconciliationResult,
)
from proofloop.agents.execution import AgentFailure, FailureCategory
from proofloop.agents.mcp.tool_specs import (
    DuplicateCheckTool,
    DuplicateQuery,
    PurchaseOrderQuery,
    PurchaseOrderTool,
    ToolError,
    VendorQuery,
    VendorTool,
)
from proofloop.agents.policy import PolicyConfig, evaluate_policy

_TOOL_FAIL_ACTION = "Retry later or route to a human reviewer; authoritative records were unavailable."


def run_reconciliation(
    *,
    extraction: ExtractedInvoice,
    purchase_order_tool: PurchaseOrderTool,
    vendor_tool: VendorTool,
    duplicate_tool: DuplicateCheckTool,
    config: PolicyConfig | None = None,
) -> ReconciliationResult | AgentFailure:
    """Reconcile a validated extraction against authoritative facts.

    Returns a `ReconciliationResult` (deterministic findings + policy decision)
    or a typed `AgentFailure` if a tool is unavailable. Never raises for tool
    problems and never reaches a payment action.
    """

    config = config or PolicyConfig()

    try:
        purchase_order = (
            purchase_order_tool.get_purchase_order(
                PurchaseOrderQuery(po_number=extraction.po_number)
            )
            if extraction.po_number is not None
            else None
        )
        vendor = vendor_tool.get_vendor_record(
            VendorQuery(
                vendor_id=extraction.vendor_id,
                vendor_name=extraction.vendor_name,
            )
        )
        duplicate = duplicate_tool.check_duplicate_invoice(
            DuplicateQuery(
                vendor_name=extraction.vendor_name,
                invoice_number=extraction.invoice_number,
                total=extraction.total,
            )
        )
    except ToolError as error:
        return AgentFailure(
            category=FailureCategory.TOOL_ERROR,
            message=f"A reconciliation tool was unavailable: {error}",
            attempts=0,
            safe_next_action=_TOOL_FAIL_ACTION,
            document_id=extraction.document_id,
        )

    mismatches: list[Mismatch] = []
    matched_facts: MatchedFacts | None = None

    # Purchase order — authoritative facts come only from the tool record.
    if extraction.po_number is None:
        mismatches.append(
            Mismatch(
                category=MismatchCategory.PO_NOT_FOUND,
                detail="The invoice carries no purchase-order number.",
            )
        )
    elif purchase_order is None:
        mismatches.append(
            Mismatch(
                category=MismatchCategory.PO_NOT_FOUND,
                detail="No purchase order matched the invoice PO number.",
                observed=extraction.po_number,
            )
        )
    else:
        matched_facts = MatchedFacts(
            po_number=purchase_order.po_number,
            vendor_id=purchase_order.vendor_id,
            vendor_name=purchase_order.vendor_name,
            po_total=purchase_order.total,
            po_currency=purchase_order.currency,
        )
        if purchase_order.currency != extraction.currency:
            mismatches.append(
                Mismatch(
                    category=MismatchCategory.CURRENCY_MISMATCH,
                    detail="Invoice currency differs from the purchase order.",
                    expected=purchase_order.currency,
                    observed=extraction.currency,
                )
            )
        if abs(purchase_order.total - extraction.total) > config.amount_tolerance:
            mismatches.append(
                Mismatch(
                    category=MismatchCategory.AMOUNT_MISMATCH,
                    detail="Invoice total differs from the purchase order beyond tolerance.",
                    expected=str(purchase_order.total),
                    observed=str(extraction.total),
                )
            )

    # Vendor — unknown or inactive vendor is a blocking mismatch.
    if vendor is None or not vendor.active:
        mismatches.append(
            Mismatch(
                category=MismatchCategory.UNKNOWN_VENDOR,
                detail="Vendor is not an active, approved vendor.",
                observed=extraction.vendor_name,
            )
        )

    findings = ReconciliationFindings(
        document_id=extraction.document_id,
        matched_facts=matched_facts,
        mismatches=tuple(mismatches),
        duplicate_status=duplicate.status,
        model_reported_confidence=extraction.model_reported_confidence,
    )
    decision = evaluate_policy(extraction=extraction, findings=findings, config=config)
    return ReconciliationResult(findings=findings, decision=decision)
