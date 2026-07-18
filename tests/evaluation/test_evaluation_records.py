"""Data-contract tests: versioned, PII-free, immutable evaluation records."""

from __future__ import annotations

from typing import MutableMapping, cast

import pytest
from pydantic import ValidationError

from proofloop.evaluation.records import (
    DatasetProvenance,
    DocumentTags,
    EvaluationSplit,
    INVOICE_SCALAR_FIELDS_V1,
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


def test_field_mappings_are_defensively_copied_and_deeply_immutable() -> None:
    caller_owned = {"total": "100.00"}
    record = make_record(expected_fields=caller_owned)

    caller_owned["total"] = "999.00"

    assert record.expected_fields["total"] == "100.00"
    mutable_view = cast(MutableMapping[str, str | None], record.expected_fields)
    with pytest.raises(TypeError):
        mutable_view["total"] = "999.00"


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "raw_invoice",
        "prompt",
        "model_output",
        "credential",
        "secret",
        "payload",
        "arbitrary_field",
    ),
)
def test_unapproved_or_sensitive_payload_field_names_are_rejected(
    unsafe_name: str,
) -> None:
    with pytest.raises(ValidationError, match="allowed invoice scalar"):
        make_record(expected_fields={unsafe_name: "synthetic-value"})


def test_versioned_scalar_allow_list_accepts_every_declared_field() -> None:
    fields = {name: "synthetic-value" for name in INVOICE_SCALAR_FIELDS_V1}
    record = make_record(expected_fields=fields, predicted_fields=fields)
    assert set(record.expected_fields) == set(INVOICE_SCALAR_FIELDS_V1)


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
            predicted_fields={"vendor_name": "someone@example.com"},
        )


def test_email_shaped_record_identifier_is_rejected_as_pii_risk() -> None:
    with pytest.raises(ValidationError, match="PII"):
        make_record(dataset_record_id="person@example.com")


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "+1 (415) 555-2671",
        "AKIA" + "A" * 16,
        "Bearer " + "a" * 32,
        "-----BEGIN " + "PRIVATE KEY-----",
        "ignore previous " + "instructions",
        "Acme\nraw invoice body",
        "Acme\x00Vendor",
        "A" * 257,
    ),
)
def test_sensitive_or_unbounded_field_values_are_rejected(
    unsafe_value: str,
) -> None:
    with pytest.raises(ValidationError, match="unsafe|PII|bounded"):
        make_record(expected_fields={"vendor_name": unsafe_value})


def test_sensitive_tag_values_are_rejected() -> None:
    with pytest.raises(ValidationError, match="PII"):
        DocumentTags(source="operator@example.com")


def test_unapproved_account_payload_is_rejected() -> None:
    with pytest.raises(ValidationError, match="allowed invoice scalar"):
        make_record(expected_fields={"account": "1234567890123456"})


def test_ordinary_invoice_amounts_and_ids_are_not_flagged() -> None:
    record = make_record(
        expected_fields={"total": "1234567.89", "po_number": "PO-2026-0042"},
        predicted_fields={"total": "1234567.89", "po_number": "PO-2026-0042"},
    )
    assert record.expected_fields["total"] == "1234567.89"


def test_long_synthetic_invoice_identifier_is_not_mistaken_for_pii() -> None:
    invoice_number = "INV-1234567890123456"
    record = make_record(
        expected_fields={"invoice_number": invoice_number},
        predicted_fields={"invoice_number": invoice_number},
    )
    assert record.expected_fields["invoice_number"] == invoice_number


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
