"""Data-contract tests: versioned, PII-free, immutable evaluation records."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from proofloop.evaluation.records import (
    DatasetProvenance,
    EvaluationSplit,
)
from .eval_fixtures import make_dataset, make_record


def test_a_valid_record_round_trips_with_schema_version() -> None:
    record = make_record()
    assert record.schema_version == "1.0.0"
    assert record.dataset_provenance is DatasetProvenance.SYNTHETIC
    assert record.split is EvaluationSplit.DEVELOPMENT


def test_records_are_immutable() -> None:
    record = make_record()
    with pytest.raises(ValidationError):
        record.latency_ms = 1  # type: ignore[misc]


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_record(raw_invoice_text="should never be stored")


def test_unknown_schema_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_record(schema_version="0.9.0")


def test_confidence_above_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_record(model_reported_confidence=1.5)


def test_confidence_below_zero_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_record(model_reported_confidence=-0.1)


def test_missing_confidence_stays_none_and_never_becomes_zero() -> None:
    record = make_record(model_reported_confidence=None)
    assert record.model_reported_confidence is None


def test_negative_latency_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_record(latency_ms=-1)


def test_email_shaped_field_value_is_rejected_as_pii_risk() -> None:
    with pytest.raises(ValidationError, match="PII"):
        make_record(
            predicted_fields={"vendor_contact": "someone@example.com"},
        )


def test_long_digit_run_field_value_is_rejected_as_pii_risk() -> None:
    with pytest.raises(ValidationError, match="PII"):
        make_record(expected_fields={"account": "1234567890123456"})


def test_ordinary_invoice_amounts_and_ids_are_not_flagged() -> None:
    record = make_record(
        expected_fields={"total": "1234567.89", "po_number": "PO-2026-0042"},
        predicted_fields={"total": "1234567.89", "po_number": "PO-2026-0042"},
    )
    assert record.expected_fields["total"] == "1234567.89"


def test_same_record_id_in_two_splits_is_split_leakage() -> None:
    development = make_record(dataset_record_id="rec-9")
    holdout = make_record(dataset_record_id="rec-9", split=EvaluationSplit.HOLDOUT)
    with pytest.raises(ValidationError, match="leakage"):
        make_dataset(development, holdout)


def test_duplicate_record_id_in_one_split_is_rejected() -> None:
    first = make_record(dataset_record_id="rec-9")
    second = make_record(dataset_record_id="rec-9")
    with pytest.raises(ValidationError, match="duplicate"):
        make_dataset(first, second)


def test_an_empty_dataset_is_valid_input_for_the_report_layer() -> None:
    dataset = make_dataset()
    assert dataset.records == ()
