from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from agent_fixtures import extracted_invoice
from proofloop.agents.contracts import (
    Disposition,
    DuplicateStatus,
    MatchedFacts,
    Mismatch,
    MismatchCategory,
    ReconciliationFindings,
)
from proofloop.agents.policy import PolicyConfig, evaluate_policy


def _findings(
    *,
    document_id: str = "doc-1",
    matched_facts: MatchedFacts | None = None,
    mismatches: tuple[Mismatch, ...] = (),
    duplicate_status: DuplicateStatus = DuplicateStatus.NOT_DUPLICATE,
    model_reported_confidence: float | None = None,
) -> ReconciliationFindings:
    return ReconciliationFindings(
        document_id=document_id,
        matched_facts=matched_facts,
        mismatches=mismatches,
        duplicate_status=duplicate_status,
        model_reported_confidence=model_reported_confidence,
    )


def test_clean_invoice_only_proceeds_to_policy_evaluation() -> None:
    decision = evaluate_policy(
        extraction=extracted_invoice(),
        findings=_findings(),
        config=PolicyConfig(),
    )
    assert decision.disposition is Disposition.ACCEPT_FOR_POLICY_EVALUATION
    assert decision.triggered_rules == ()


def test_high_value_invoice_requires_human_review() -> None:
    decision = evaluate_policy(
        extraction=extracted_invoice(
            subtotal="20000.00",
            tax="0.00",
            total="20000.00",
            line_items=[
                {
                    "description": "Server",
                    "quantity": "1",
                    "unit_price": "20000.00",
                    "tax": "0.00",
                    "line_total": "20000.00",
                }
            ],
        ),
        findings=_findings(),
        config=PolicyConfig(high_value_threshold=Decimal("10000.00")),
    )
    assert decision.disposition is Disposition.HUMAN_REVIEW
    assert "HIGH_VALUE_REVIEW" in decision.triggered_rules


def test_low_confidence_requires_human_review() -> None:
    decision = evaluate_policy(
        extraction=extracted_invoice(model_reported_confidence=0.20),
        findings=_findings(),
        config=PolicyConfig(min_extraction_confidence=0.70),
    )
    assert decision.disposition is Disposition.HUMAN_REVIEW
    assert "LOW_CONFIDENCE_REVIEW" in decision.triggered_rules


def test_missing_confidence_requires_human_review() -> None:
    decision = evaluate_policy(
        extraction=extracted_invoice(model_reported_confidence=None),
        findings=_findings(),
        config=PolicyConfig(),
    )
    assert decision.disposition is Disposition.HUMAN_REVIEW


def test_block_dominates_review() -> None:
    decision = evaluate_policy(
        extraction=extracted_invoice(model_reported_confidence=0.10),  # would review
        findings=_findings(duplicate_status=DuplicateStatus.CONFIRMED_DUPLICATE),  # blocks
        config=PolicyConfig(),
    )
    assert decision.disposition is Disposition.BLOCK


def test_thresholds_are_configurable_and_change_outcome() -> None:
    invoice = extracted_invoice(model_reported_confidence=0.60)
    strict = evaluate_policy(
        extraction=invoice, findings=_findings(), config=PolicyConfig(min_extraction_confidence=0.70)
    )
    lenient = evaluate_policy(
        extraction=invoice, findings=_findings(), config=PolicyConfig(min_extraction_confidence=0.50)
    )
    assert strict.disposition is Disposition.HUMAN_REVIEW
    assert lenient.disposition is Disposition.ACCEPT_FOR_POLICY_EVALUATION


def test_decimal_high_value_boundary_is_exact() -> None:
    # Exactly at threshold triggers review; one cent below does not.
    at = extracted_invoice(
        subtotal="10000.00", tax="0.00", total="10000.00",
        line_items=[{"description": "x", "quantity": "1", "unit_price": "10000.00", "tax": "0.00", "line_total": "10000.00"}],
    )
    below = extracted_invoice(
        subtotal="9999.99", tax="0.00", total="9999.99",
        line_items=[{"description": "x", "quantity": "1", "unit_price": "9999.99", "tax": "0.00", "line_total": "9999.99"}],
    )
    config = PolicyConfig(high_value_threshold=Decimal("10000.00"))
    assert evaluate_policy(extraction=at, findings=_findings(), config=config).disposition is Disposition.HUMAN_REVIEW
    assert evaluate_policy(extraction=below, findings=_findings(), config=config).disposition is Disposition.ACCEPT_FOR_POLICY_EVALUATION


def test_amount_tolerance_is_configurable() -> None:
    findings = _findings(
        mismatches=(
            Mismatch(category=MismatchCategory.AMOUNT_MISMATCH, detail="differs"),
        )
    )
    decision = evaluate_policy(
        extraction=extracted_invoice(), findings=findings, config=PolicyConfig()
    )
    assert decision.disposition is Disposition.HUMAN_REVIEW


def test_missing_po_disposition_cannot_be_auto_accept() -> None:
    with pytest.raises(ValidationError):
        PolicyConfig(missing_po_disposition=Disposition.ACCEPT_FOR_POLICY_EVALUATION)


def test_policy_is_deterministic() -> None:
    invoice = extracted_invoice()
    findings = _findings()
    config = PolicyConfig()
    first = evaluate_policy(extraction=invoice, findings=findings, config=config)
    second = evaluate_policy(extraction=invoice, findings=findings, config=config)
    assert first == second
