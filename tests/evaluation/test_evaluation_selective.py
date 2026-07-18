"""Selective-risk and cost-sensitive threshold-sweep tests (decision support)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from proofloop.evaluation.calibration import (
    selective_risk_table,
    threshold_cost_sweep,
)
from .eval_fixtures import make_record

_WRONG_PREDICTION = {
    "invoice_number": "INV-9999",
    "vendor_name": "Acme GmbH",
    "total": "100.00",
}


def _records():  # type: ignore[no-untyped-def]
    return (
        make_record(dataset_record_id="r1", model_reported_confidence=0.9),
        make_record(dataset_record_id="r2", model_reported_confidence=0.8),
        make_record(
            dataset_record_id="r3",
            model_reported_confidence=0.7,
            predicted_fields=_WRONG_PREDICTION,
        ),
        make_record(dataset_record_id="r4", model_reported_confidence=None),
    )


def _row(table, threshold: str):  # type: ignore[no-untyped-def]
    rows = [row for row in table.rows if row.threshold == threshold]
    assert rows, f"missing threshold {threshold}"
    return rows[0]


def test_coverage_and_accuracy_at_each_threshold() -> None:
    table = selective_risk_table(
        _records(), thresholds=(Decimal("0"), Decimal("0.75"))
    )
    at_zero = _row(table, "0")
    # Missing confidence can never be auto-accepted: 3 of 4 covered.
    assert at_zero.covered == 3
    assert at_zero.coverage == "0.75"
    assert at_zero.accuracy_on_covered == "0.666666666667"
    assert at_zero.risk_on_covered == "0.333333333333"

    at_075 = _row(table, "0.75")
    assert at_075.covered == 2
    assert at_075.coverage == "0.5"
    assert at_075.accuracy_on_covered == "1"
    assert at_075.risk_on_covered == "0"


def test_a_threshold_covering_nothing_reports_no_accuracy() -> None:
    table = selective_risk_table(_records(), thresholds=(Decimal("0.99"),))
    row = _row(table, "0.99")
    assert row.covered == 0
    assert row.accuracy_on_covered is None


def test_cost_sweep_uses_caller_supplied_costs_only() -> None:
    sweep = threshold_cost_sweep(
        _records(),
        review_cost=Decimal("1"),
        error_cost=Decimal("10"),
        thresholds=(Decimal("0"), Decimal("0.75")),
    )
    at_zero = _row(sweep, "0")
    # 1 uncovered (missing confidence) * 1 + 1 wrong covered * 10, over 4.
    assert at_zero.expected_cost_per_invoice == "2.75"
    at_075 = _row(sweep, "0.75")
    # 2 uncovered * 1 + 0 wrong covered, over 4.
    assert at_075.expected_cost_per_invoice == "0.5"
    assert sweep.lowest_cost_threshold == "0.75"


def test_cost_sweep_is_labeled_decision_support_not_a_verdict() -> None:
    sweep = threshold_cost_sweep(
        _records(),
        review_cost=Decimal("1"),
        error_cost=Decimal("10"),
        thresholds=(Decimal("0.5"),),
    )
    assert "decision support" in sweep.disclaimer.lower()
    assert "verdict" in sweep.disclaimer.lower()


def test_unjudgeable_or_incomplete_records_always_route_to_review() -> None:
    unjudgeable = make_record(
        dataset_record_id="u1",
        expected_fields={},
        predicted_fields={},
        model_reported_confidence=1.0,
    )
    incomplete = make_record(
        dataset_record_id="u2",
        expected_fields={"invoice_number": "INV-1001", "total": "10.00"},
        predicted_fields={"invoice_number": "INV-1001"},
        model_reported_confidence=1.0,
    )
    sweep = threshold_cost_sweep(
        (unjudgeable, incomplete),
        review_cost=Decimal("1"),
        error_cost=Decimal("10"),
        thresholds=(Decimal("0"),),
    )
    row = _row(sweep, "0")
    assert row.auto_accepted == 0
    assert row.routed_to_review == 2
    assert row.wrong_auto_accepts == 0
    assert row.expected_cost_per_invoice == "1"


def test_empty_records_produce_an_empty_table_not_a_crash() -> None:
    table = selective_risk_table((), thresholds=(Decimal("0.5"),))
    row = _row(table, "0.5")
    assert row.covered == 0
    assert row.coverage is None


@pytest.mark.parametrize("invalid", ("-1", "NaN", "Infinity", "-Infinity"))
def test_cost_sweep_rejects_negative_or_non_finite_costs(invalid: str) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        threshold_cost_sweep(
            _records(),
            review_cost=Decimal(invalid),
            error_cost=Decimal("1"),
        )
    with pytest.raises(ValueError, match="finite non-negative"):
        threshold_cost_sweep(
            _records(),
            review_cost=Decimal("1"),
            error_cost=Decimal(invalid),
        )


def test_cost_sweep_accepts_zero_costs() -> None:
    sweep = threshold_cost_sweep(
        _records(),
        review_cost=Decimal("0"),
        error_cost=Decimal("0"),
        thresholds=(Decimal("0.5"),),
    )
    assert sweep.rows[0].expected_cost_per_invoice == "0"
