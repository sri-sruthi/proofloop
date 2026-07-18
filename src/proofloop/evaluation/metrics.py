"""Deterministic match, numeric-error, parseability, and summary metrics.

Every result declares its numerator, denominator, sample count, missing-value
counts, sufficiency, and limitations. A zero denominator yields value None and
INSUFFICIENT_EVIDENCE — never a fabricated number. All arithmetic is Decimal;
serialized values use one canonical fixed-point formatter.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from math import ceil

from proofloop.evaluation.normalization import (
    NUMERIC_FIELD_NAMES,
    canonical_decimal_string,
    normalize_text,
    parse_amount,
)
from proofloop.evaluation.records import EvaluationModel, EvaluationRecord


class MetricKind(str, Enum):
    """What a number is for; a reader must never have to guess."""

    DESCRIPTIVE = "DESCRIPTIVE"
    CALIBRATION = "CALIBRATION"
    DECISION_SUPPORT = "DECISION_SUPPORT"


class SufficiencyStatus(str, Enum):
    """Whether the evidence behind a value supports reading it at all."""

    OK = "OK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"


class MetricResult(EvaluationModel):
    """One metric with its full evidence accounting."""

    metric_id: str
    kind: MetricKind
    numerator: str
    denominator: str
    value: str | None
    sample_count: int
    excluded_missing: int = 0
    excluded_zero_denominator: int = 0
    sufficiency: SufficiencyStatus
    limitations: tuple[str, ...] = ()


class LatencySummary(EvaluationModel):
    """Order statistics over latency_ms (nearest-rank p95)."""

    kind: MetricKind = MetricKind.DESCRIPTIVE
    sample_count: int
    minimum: str | None
    maximum: str | None
    mean: str | None
    median: str | None
    p95: str | None
    sufficiency: SufficiencyStatus


class TokenSummary(EvaluationModel):
    """Token totals/means; missing values are counted, never zeroed."""

    kind: MetricKind = MetricKind.DESCRIPTIVE
    input_sample_count: int
    input_missing: int
    input_total: str | None
    input_mean: str | None
    output_sample_count: int
    output_missing: int
    output_total: str | None
    output_mean: str | None
    sufficiency: SufficiencyStatus


_FIXTURE_NOTE = (
    "When labels are synthetic fixtures this is harness/fixture agreement, "
    "not production accuracy."
)


def _ratio(numerator: Decimal | int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return canonical_decimal_string(Decimal(numerator) / Decimal(denominator))


def _sufficiency(denominator: int) -> SufficiencyStatus:
    if denominator == 0:
        return SufficiencyStatus.INSUFFICIENT_EVIDENCE
    return SufficiencyStatus.OK


def _values_match(
    expected: str | None, predicted: str | None, *, normalized: bool
) -> bool:
    if expected is None or predicted is None:
        return expected is None and predicted is None
    if normalized:
        return normalize_text(expected) == normalize_text(predicted)
    return expected == predicted


def field_match_results(
    records: tuple[EvaluationRecord, ...], *, normalized: bool
) -> tuple[MetricResult, ...]:
    """Per-field match rate over every field any record expects."""

    if not records:
        return ()
    prefix = "field_normalized_match" if normalized else "field_exact_match"
    field_names = sorted(
        {name for record in records for name in record.expected_fields}
    )
    results: list[MetricResult] = []
    for name in field_names:
        denominator = 0
        numerator = 0
        for record in records:
            if name not in record.expected_fields:
                continue
            denominator += 1
            predicted = record.predicted_fields.get(name)
            if name in record.predicted_fields and _values_match(
                record.expected_fields[name], predicted, normalized=normalized
            ):
                numerator += 1
        results.append(
            MetricResult(
                metric_id=f"{prefix}:{name}",
                kind=MetricKind.DESCRIPTIVE,
                numerator=str(numerator),
                denominator=str(denominator),
                value=_ratio(numerator, denominator),
                sample_count=len(records),
                sufficiency=_sufficiency(denominator),
                limitations=(_FIXTURE_NOTE,),
            )
        )
    return tuple(results)


def invoice_is_correct(record: EvaluationRecord) -> bool | None:
    """Invoice-level correctness: every expected field normalized-matches.

    Returns None when the record has no expected fields, because correctness
    is then unjudgeable; such records are excluded and counted, never scored.
    """

    if not record.expected_fields:
        return None
    for name, expected in record.expected_fields.items():
        if name not in record.predicted_fields:
            return False
        if not _values_match(
            expected, record.predicted_fields[name], normalized=True
        ):
            return False
    return True


def invoice_exact_match(
    records: tuple[EvaluationRecord, ...],
) -> MetricResult:
    """Share of judgeable invoices whose every expected field matches."""

    numerator = 0
    denominator = 0
    excluded = 0
    for record in records:
        verdict = invoice_is_correct(record)
        if verdict is None:
            excluded += 1
            continue
        denominator += 1
        if verdict:
            numerator += 1
    return MetricResult(
        metric_id="invoice_exact_match",
        kind=MetricKind.DESCRIPTIVE,
        numerator=str(numerator),
        denominator=str(denominator),
        value=_ratio(numerator, denominator),
        sample_count=len(records),
        excluded_missing=excluded,
        sufficiency=_sufficiency(denominator),
        limitations=(
            "Comparison uses the documented conservative normalization.",
            _FIXTURE_NOTE,
        ),
    )


def numeric_error_results(
    records: tuple[EvaluationRecord, ...],
) -> tuple[MetricResult, ...]:
    """Mean absolute and mean relative error per numeric field."""

    field_names = sorted(
        {
            name
            for record in records
            for name in record.expected_fields
            if name in NUMERIC_FIELD_NAMES
        }
    )
    results: list[MetricResult] = []
    for name in field_names:
        pairs: list[tuple[Decimal, Decimal]] = []
        unparseable = 0
        for record in records:
            if name not in record.expected_fields:
                continue
            expected = parse_amount(record.expected_fields[name])
            predicted = parse_amount(record.predicted_fields.get(name))
            if expected is None or predicted is None:
                unparseable += 1
                continue
            pairs.append((expected, predicted))

        absolute_sum = sum(
            (abs(predicted - expected) for expected, predicted in pairs),
            Decimal(0),
        )
        results.append(
            MetricResult(
                metric_id=f"absolute_numeric_error:{name}",
                kind=MetricKind.DESCRIPTIVE,
                numerator=canonical_decimal_string(absolute_sum),
                denominator=str(len(pairs)),
                value=(
                    canonical_decimal_string(absolute_sum / len(pairs))
                    if pairs
                    else None
                ),
                sample_count=len(records),
                excluded_missing=unparseable,
                sufficiency=_sufficiency(len(pairs)),
                limitations=(
                    "Unparseable amounts are excluded and counted, never "
                    "guessed.",
                ),
            )
        )

        relative_pairs = [
            (expected, predicted)
            for expected, predicted in pairs
            if expected != 0
        ]
        zero_denominators = len(pairs) - len(relative_pairs)
        relative_sum = sum(
            (
                abs(predicted - expected) / abs(expected)
                for expected, predicted in relative_pairs
            ),
            Decimal(0),
        )
        results.append(
            MetricResult(
                metric_id=f"relative_numeric_error:{name}",
                kind=MetricKind.DESCRIPTIVE,
                numerator=canonical_decimal_string(relative_sum),
                denominator=str(len(relative_pairs)),
                value=(
                    canonical_decimal_string(
                        relative_sum / len(relative_pairs)
                    )
                    if relative_pairs
                    else None
                ),
                sample_count=len(records),
                excluded_missing=unparseable,
                excluded_zero_denominator=zero_denominators,
                sufficiency=_sufficiency(len(relative_pairs)),
                limitations=(
                    "Records whose expected value is zero are excluded from "
                    "the relative-error mean (zero denominator) and counted "
                    "in excluded_zero_denominator.",
                ),
            )
        )
    return tuple(results)


def numeric_prediction_parse_availability_rate(
    records: tuple[EvaluationRecord, ...],
) -> MetricResult:
    """Share with every expected numeric prediction present and parseable."""

    numerator = 0
    denominator = 0
    excluded_missing = 0
    for record in records:
        expected_numeric_fields = tuple(
            name for name in record.expected_fields if name in NUMERIC_FIELD_NAMES
        )
        if not expected_numeric_fields:
            excluded_missing += 1
            continue
        denominator += 1
        valid = all(
            name in record.predicted_fields
            and parse_amount(record.predicted_fields[name]) is not None
            for name in expected_numeric_fields
        )
        if valid:
            numerator += 1
    return MetricResult(
        metric_id="numeric_prediction_parse_availability_rate",
        kind=MetricKind.DESCRIPTIVE,
        numerator=str(numerator),
        denominator=str(denominator),
        value=_ratio(numerator, denominator),
        sample_count=len(records),
        excluded_missing=excluded_missing,
        sufficiency=_sufficiency(denominator),
        limitations=(
            "This measures availability and conservative parseability only; "
            "it is not extraction-schema validation.",
            "Records with no expected numeric field are excluded and counted.",
        ),
    )


def latency_summary(
    records: tuple[EvaluationRecord, ...],
) -> LatencySummary:
    values = sorted(Decimal(record.latency_ms) for record in records)
    count = len(values)
    if count == 0:
        return LatencySummary(
            sample_count=0,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            p95=None,
            sufficiency=SufficiencyStatus.INSUFFICIENT_EVIDENCE,
        )
    if count % 2 == 1:
        median = values[count // 2]
    else:
        median = (values[count // 2 - 1] + values[count // 2]) / 2
    p95_rank = max(1, ceil(Decimal("0.95") * count))
    return LatencySummary(
        sample_count=count,
        minimum=canonical_decimal_string(values[0]),
        maximum=canonical_decimal_string(values[-1]),
        mean=canonical_decimal_string(sum(values, Decimal(0)) / count),
        median=canonical_decimal_string(median),
        p95=canonical_decimal_string(values[p95_rank - 1]),
        sufficiency=SufficiencyStatus.OK,
    )


def _token_stats(
    values: tuple[int | None, ...],
) -> tuple[int, int, str | None, str | None]:
    present = [Decimal(value) for value in values if value is not None]
    missing = len(values) - len(present)
    if not present:
        return 0, missing, None, None
    total = sum(present, Decimal(0))
    return (
        len(present),
        missing,
        canonical_decimal_string(total),
        canonical_decimal_string(total / len(present)),
    )


def token_summary(records: tuple[EvaluationRecord, ...]) -> TokenSummary:
    in_count, in_missing, in_total, in_mean = _token_stats(
        tuple(record.input_tokens for record in records)
    )
    out_count, out_missing, out_total, out_mean = _token_stats(
        tuple(record.output_tokens for record in records)
    )
    return TokenSummary(
        input_sample_count=in_count,
        input_missing=in_missing,
        input_total=in_total,
        input_mean=in_mean,
        output_sample_count=out_count,
        output_missing=out_missing,
        output_total=out_total,
        output_mean=out_mean,
        sufficiency=_sufficiency(max(in_count, out_count)),
    )
