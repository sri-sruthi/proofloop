"""Calibration tests: Brier, bins, ECE — confidence versus observed correctness.

The binary target throughout is invoice-level normalized match (documented in
the metric limitations). Records without a confidence value are excluded and
counted; they are never treated as confidence 0.
"""

from __future__ import annotations

from proofloop.evaluation.calibration import (
    brier_score,
    calibration_bins,
    expected_calibration_error,
)
from proofloop.evaluation.metrics import MetricKind, SufficiencyStatus
from .eval_fixtures import make_record

_WRONG_PREDICTION = {
    "invoice_number": "INV-9999",
    "vendor_name": "Acme GmbH",
    "total": "100.00",
}


def _correct(record_id: str, confidence: float | None):  # type: ignore[no-untyped-def]
    return make_record(
        dataset_record_id=record_id, model_reported_confidence=confidence
    )


def _incorrect(  # type: ignore[no-untyped-def]
    record_id: str, confidence: float | None
):
    return make_record(
        dataset_record_id=record_id,
        model_reported_confidence=confidence,
        predicted_fields=_WRONG_PREDICTION,
    )


def test_brier_score_matches_a_hand_computed_example() -> None:
    records = (
        _correct("r1", 1.0),  # (1.0 - 1)^2 = 0
        _incorrect("r2", 0.0),  # (0.0 - 0)^2 = 0
        _correct("r3", 0.5),  # (0.5 - 1)^2 = 0.25
        _incorrect("r4", 0.8),  # (0.8 - 0)^2 = 0.64
    )
    result = brier_score(records)
    assert result.value == "0.2225"
    assert result.denominator == "4"
    assert result.kind is MetricKind.CALIBRATION


def test_missing_confidence_is_excluded_never_coerced_to_zero() -> None:
    records = (
        _correct("r1", None),
        _correct("r2", 0.5),
    )
    result = brier_score(records)
    # Only r2 participates: (0.5 - 1)^2 = 0.25. If None became 0.0 the value
    # would be 0.625.
    assert result.value == "0.25"
    assert result.denominator == "1"
    assert result.excluded_missing == 1


def test_brier_over_no_confident_records_is_insufficient_evidence() -> None:
    result = brier_score((_correct("r1", None),))
    assert result.value is None
    assert result.sufficiency is SufficiencyStatus.INSUFFICIENT_EVIDENCE


def test_calibration_bins_are_fixed_width_with_right_closed_last_bin() -> None:
    records = (
        _incorrect("r1", 0.05),
        _correct("r2", 0.1),  # boundary: belongs to [0.1, 0.2)
        _correct("r3", 1.0),  # boundary: belongs to [0.9, 1.0]
    )
    table = calibration_bins(records)
    assert len(table.bins) == 10
    first, second, last = table.bins[0], table.bins[1], table.bins[9]
    assert (first.lower, first.upper, first.count) == ("0", "0.1", 1)
    assert (second.lower, second.upper, second.count) == ("0.1", "0.2", 1)
    assert (last.lower, last.upper, last.count) == ("0.9", "1", 1)
    assert first.observed_rate == "0"
    assert second.observed_rate == "1"


def test_empty_bins_report_no_rate_instead_of_zero() -> None:
    table = calibration_bins((_correct("r1", 0.95),))
    middle = table.bins[4]
    assert middle.count == 0
    assert middle.observed_rate is None
    assert middle.mean_confidence is None


def test_expected_calibration_error_matches_a_hand_computed_example() -> None:
    records = (
        _incorrect("r1", 0.05),  # bin0: acc 0, conf 0.05 -> |0 - 0.05| = 0.05
        _correct("r2", 0.95),  # bin9: acc 0.5, conf 0.95 -> |0.5 - 0.95| = 0.45
        _incorrect("r3", 0.95),
    )
    result = expected_calibration_error(records)
    # ECE = (1/3)*0.05 + (2/3)*0.45 = 0.95/3
    assert result.value == "0.316666666667"
    assert result.kind is MetricKind.CALIBRATION


def test_calibration_metrics_document_the_binary_target() -> None:
    result = brier_score((_correct("r1", 0.5),))
    assert any("invoice-level" in note for note in result.limitations)
