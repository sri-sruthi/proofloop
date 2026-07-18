"""Normalization-policy tests: conservative, documented, no aggressive merging."""

from __future__ import annotations

from decimal import Decimal

from proofloop.evaluation.normalization import (
    NUMERIC_FIELD_NAMES,
    canonical_decimal_string,
    normalize_text,
    parse_amount,
)


def test_unicode_nfkc_whitespace_and_case_are_normalized() -> None:
    assert normalize_text("  Acme  GmbH  ") == "acme gmbh"
    # NFKC folds the ligature "ﬃ" into "ffi".
    assert normalize_text("Oﬃce Supplies") == "office supplies"


def test_internal_whitespace_runs_collapse_to_one_space() -> None:
    assert normalize_text("INV \t\n 1001") == "inv 1001"


def test_casefold_handles_non_ascii_case() -> None:
    assert normalize_text("Straße") == "strasse"


def test_parse_amount_accepts_plain_decimal_strings() -> None:
    assert parse_amount("100.00") == Decimal("100.00")
    assert parse_amount(" -42.5 ") == Decimal("-42.5")
    assert parse_amount("+7") == Decimal("7")


def test_parse_amount_rejects_currency_symbols_and_separators() -> None:
    # Conservative policy: "1,234" is NOT silently equal to "1234".
    assert parse_amount("$100.00") is None
    assert parse_amount("1,234") is None
    assert parse_amount("1.234,56") is None
    assert parse_amount("") is None
    assert parse_amount(None) is None
    assert parse_amount("12.3.4") is None


def test_normalization_never_makes_different_amounts_equal() -> None:
    assert normalize_text("100.00") != normalize_text("100.01")
    assert parse_amount("100") == Decimal("100.00")  # numeric, not string, equality


def test_numeric_field_names_cover_the_invoice_money_fields() -> None:
    assert {"total", "subtotal", "tax"} <= set(NUMERIC_FIELD_NAMES)


def test_canonical_decimal_string_is_fixed_point_without_noise() -> None:
    assert canonical_decimal_string(Decimal("0.222500000000")) == "0.2225"
    assert canonical_decimal_string(Decimal("100")) == "100"
    assert canonical_decimal_string(Decimal("1") / Decimal("3")) == "0.333333333333"
    assert canonical_decimal_string(Decimal("0")) == "0"
