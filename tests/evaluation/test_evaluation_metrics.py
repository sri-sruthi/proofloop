"""Match, numeric-error, schema-rate, and summary metric tests."""

from __future__ import annotations

import pytest

from proofloop.evaluation.metrics import (
    MetricKind,
    SufficiencyStatus,
    field_match_results,
    invoice_exact_match,
    latency_summary,
    numeric_prediction_parse_availability_rate,
    numeric_error_results,
    token_summary,
)
from .eval_fixtures import make_record


def _by_id(results: tuple, metric_id: str):  # type: ignore[type-arg]
    matches = [r for r in results if r.metric_id == metric_id]
    assert matches, f"missing metric {metric_id}: {[r.metric_id for r in results]}"
    return matches[0]


def test_field_exact_match_counts_raw_string_equality() -> None:
    exact = make_record(dataset_record_id="r1")
    near = make_record(
        dataset_record_id="r2",
        predicted_fields={
            "invoice_number": "INV-1001",
            "vendor_name": "acme  gmbh",
            "total": "100.00",
        },
    )
    results = field_match_results((exact, near), normalized=False)
    vendor = _by_id(results, "field_exact_match:vendor_name")
    assert vendor.numerator == "1"
    assert vendor.denominator == "2"
    assert vendor.value == "0.5"
    assert vendor.kind is MetricKind.DESCRIPTIVE


def test_field_normalized_match_forgives_case_and_whitespace_only() -> None:
    near = make_record(
        predicted_fields={
            "invoice_number": "INV-1001",
            "vendor_name": "acme  gmbh",
            "total": "100.00",
        },
    )
    results = field_match_results((near,), normalized=True)
    vendor = _by_id(results, "field_normalized_match:vendor_name")
    assert vendor.value == "1"


def test_a_missing_predicted_field_counts_as_a_miss_not_an_error() -> None:
    record = make_record(
        predicted_fields={"invoice_number": "INV-1001", "total": "100.00"},
    )
    results = field_match_results((record,), normalized=True)
    vendor = _by_id(results, "field_normalized_match:vendor_name")
    assert vendor.numerator == "0"
    assert vendor.denominator == "1"


def test_invoice_level_exact_match_requires_every_expected_field() -> None:
    good = make_record(dataset_record_id="r1")
    bad = make_record(
        dataset_record_id="r2",
        predicted_fields={
            "invoice_number": "INV-9999",
            "vendor_name": "Acme GmbH",
            "total": "100.00",
        },
    )
    result = invoice_exact_match((good, bad))
    assert result.numerator == "1"
    assert result.denominator == "2"
    assert result.value == "0.5"


def test_invoice_match_with_no_expected_fields_is_excluded_and_counted() -> None:
    unjudgeable = make_record(expected_fields={}, predicted_fields={})
    result = invoice_exact_match((unjudgeable,))
    assert result.value is None
    assert result.excluded_missing == 1
    assert result.sufficiency is SufficiencyStatus.INSUFFICIENT_EVIDENCE


def test_zero_records_yield_insufficient_evidence_not_a_number() -> None:
    result = invoice_exact_match(())
    assert result.value is None
    assert result.denominator == "0"
    assert result.sufficiency is SufficiencyStatus.INSUFFICIENT_EVIDENCE


def test_absolute_numeric_error_uses_exact_decimals() -> None:
    off_by_ten = make_record(
        dataset_record_id="r1",
        expected_fields={"total": "100.00"},
        predicted_fields={"total": "90.00"},
    )
    exact = make_record(
        dataset_record_id="r2",
        expected_fields={"total": "50"},
        predicted_fields={"total": "50"},
    )
    results = numeric_error_results((off_by_ten, exact))
    absolute = _by_id(results, "absolute_numeric_error:total")
    assert absolute.value == "5"  # mean of 10.00 and 0
    assert absolute.denominator == "2"


def test_relative_numeric_error_documents_zero_denominator_exclusion() -> None:
    normal = make_record(
        dataset_record_id="r1",
        expected_fields={"total": "100.00"},
        predicted_fields={"total": "90.00"},
    )
    zero_expected = make_record(
        dataset_record_id="r2",
        expected_fields={"total": "0"},
        predicted_fields={"total": "5"},
    )
    results = numeric_error_results((normal, zero_expected))
    relative = _by_id(results, "relative_numeric_error:total")
    assert relative.value == "0.1"
    assert relative.denominator == "1"
    assert relative.excluded_zero_denominator == 1
    assert any("zero" in note.lower() for note in relative.limitations)


def test_unparseable_amounts_are_excluded_and_counted_never_guessed() -> None:
    messy = make_record(
        expected_fields={"total": "100.00"},
        predicted_fields={"total": "1,234"},
    )
    results = numeric_error_results((messy,))
    absolute = _by_id(results, "absolute_numeric_error:total")
    assert absolute.value is None
    assert absolute.excluded_missing == 1


def test_numeric_prediction_rate_checks_parseability_and_availability() -> None:
    valid = make_record(dataset_record_id="r1")
    invalid = make_record(
        dataset_record_id="r2",
        predicted_fields={
            "invoice_number": "INV-1002",
            "vendor_name": "Acme GmbH",
            "total": "1,234",
        },
    )
    result = numeric_prediction_parse_availability_rate((valid, invalid))
    assert result.value == "0.5"
    assert result.numerator == "1"
    assert result.denominator == "2"
    assert result.metric_id == "numeric_prediction_parse_availability_rate"


def test_numeric_prediction_rate_counts_missing_expected_numeric_field_as_invalid(
) -> None:
    missing_total = make_record(
        expected_fields={"invoice_number": "INV-1001", "total": "10.00"},
        predicted_fields={"invoice_number": "INV-1001"},
    )
    result = numeric_prediction_parse_availability_rate((missing_total,))
    assert result.value == "0"
    assert result.numerator == "0"
    assert result.denominator == "1"


def test_numeric_prediction_rate_excludes_records_without_expected_numeric_fields(
) -> None:
    not_applicable = make_record(
        expected_fields={"invoice_number": "INV-1001"},
        predicted_fields={"invoice_number": "INV-1001"},
    )
    result = numeric_prediction_parse_availability_rate((not_applicable,))
    assert result.value is None
    assert result.denominator == "0"
    assert result.excluded_missing == 1
    assert result.sufficiency is SufficiencyStatus.INSUFFICIENT_EVIDENCE


def test_latency_summary_reports_deterministic_order_statistics() -> None:
    records = tuple(
        make_record(dataset_record_id=f"r{i}", latency_ms=ms)
        for i, ms in enumerate((100, 200, 300, 400))
    )
    summary = latency_summary(records)
    assert summary.sample_count == 4
    assert summary.minimum == "100"
    assert summary.maximum == "400"
    assert summary.mean == "250"
    assert summary.median == "250"
    assert summary.p95 == "400"  # nearest-rank on 4 samples


def test_latency_summary_of_zero_records_is_insufficient_evidence() -> None:
    summary = latency_summary(())
    assert summary.sample_count == 0
    assert summary.mean is None
    assert summary.sufficiency is SufficiencyStatus.INSUFFICIENT_EVIDENCE


def test_token_summary_counts_missing_values_instead_of_zeroing_them() -> None:
    with_tokens = make_record(dataset_record_id="r1", input_tokens=1000)
    without_tokens = make_record(
        dataset_record_id="r2", input_tokens=None, output_tokens=None
    )
    summary = token_summary((with_tokens, without_tokens))
    assert summary.input_sample_count == 1
    assert summary.input_missing == 1
    assert summary.input_total == "1000"


def test_every_metric_result_names_its_kind_and_counts() -> None:
    record = make_record()
    for result in field_match_results((record,), normalized=True):
        assert result.kind is MetricKind.DESCRIPTIVE
        assert result.sample_count == 1
        assert result.numerator is not None
        assert result.denominator is not None


@pytest.mark.parametrize("normalized", [False, True])
def test_match_metrics_over_empty_input_are_empty_not_crashing(
    normalized: bool,
) -> None:
    assert field_match_results((), normalized=normalized) == ()
