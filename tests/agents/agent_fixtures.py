"""Hand-authored unit fixtures for the agent foundation.

These few fixtures exist only to exercise deterministic behavior. They are NOT a
training dataset and are not evidence of real-world extraction accuracy.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from proofloop.agents.contracts import (
    ContentType,
    ExtractedInvoice,
    InvoiceInput,
    TrustedInvoiceMetadata,
)
from proofloop.agents.mcp.tool_specs import (
    PurchaseOrderRecord,
    VendorRecord,
)

UTC = timezone.utc


def valid_invoice_dict(**overrides: Any) -> dict[str, Any]:
    """A well-formed, arithmetic-consistent ExtractedInvoice payload."""

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
    return payload


def valid_invoice_json(**overrides: Any) -> str:
    return json.dumps(valid_invoice_dict(**overrides))


def extracted_invoice(**overrides: Any) -> ExtractedInvoice:
    return ExtractedInvoice.model_validate(valid_invoice_dict(**overrides))


def invoice_input(
    *,
    document_id: str = "doc-1",
    content: str = "Invoice from Acme Supplies. Total 105.00 USD.",
) -> InvoiceInput:
    return InvoiceInput(
        document_id=document_id,
        content_type=ContentType.TEXT_PLAIN,
        trusted_metadata=TrustedInvoiceMetadata(
            source_system="accounts-payable",
            received_at=datetime(2026, 7, 10, tzinfo=UTC),
        ),
        untrusted_content=content,
    )


def matching_po(**overrides: Any) -> PurchaseOrderRecord:
    data: dict[str, Any] = {
        "po_number": "PO-1",
        "vendor_id": "V1",
        "vendor_name": "Acme Supplies",
        "currency": "USD",
        "total": Decimal("105.00"),
        "status": "OPEN",
    }
    data.update(overrides)
    return PurchaseOrderRecord.model_validate(data)


def known_vendor(**overrides: Any) -> VendorRecord:
    data: dict[str, Any] = {
        "vendor_id": "V1",
        "vendor_name": "Acme Supplies",
        "active": True,
    }
    data.update(overrides)
    return VendorRecord.model_validate(data)
