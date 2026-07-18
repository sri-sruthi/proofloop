"""Calibration and selective-risk analytics (offline decision support).

Binary target throughout: invoice-level normalized match (see
``invoice_is_correct``). Records without a reported confidence are excluded
and counted — a missing confidence is unknown, not zero. Every output here is
analytical; nothing feeds a runtime compliance decision.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from proofloop.evaluation.metrics import (
    MetricKind,
    MetricResult,
    SufficiencyStatus,
    invoice_is_correct,
)
from proofloop.evaluation.normalization import canonical_decimal_string
from proofloop.evaluation.records import EvaluationModel, EvaluationRecord

_BINARY_TARGET_NOTE = (
    "Binary target is invoice-level normalized match; model-reported "
    "confidence is uncalibrated until this evidence says otherwise."
)

_DECISION_SUPPORT_DISCLAIMER = (
    "Decision support only: this table informs an offline business choice of "
    "human-review threshold. It never creates, overrides, or suppresses a "
    "runtime compliance verdict, invoice disposition, or human-review "
    "boundary."
)

DEFAULT_THRESHOLDS: tuple[Decimal, ...] = tuple(
    Decimal(step) / 10 for step in range(11)
)


class CalibrationBin(EvaluationModel):
    """One fixed-width confidence bin; empty bins report None, not zero."""

    lower: str
    upper: str
    count: int
    mean_confidence: str | None
    observed_rate: str | None


class CalibrationTable(EvaluationModel):
    bins: tuple[CalibrationBin, ...]
    sample_count: int
    excluded_missing: int
    sufficiency: SufficiencyStatus
    limitations: tuple[str, ...]


class SelectiveRiskRow(EvaluationModel):
    """Coverage/accuracy trade-off at one confidence threshold."""

    threshold: str
    covered: int
    coverage: str | None
    accuracy_on_covered: str | None
    risk_on_covered: str | None


class SelectiveRiskTable(EvaluationModel):
    rows: tuple[SelectiveRiskRow, ...]
    sample_count: int
    excluded_missing: int
    kind: MetricKind = MetricKind.DECISION_SUPPORT
    disclaimer: str = _DECISION_SUPPORT_DISCLAIMER
    limitations: tuple[str, ...] = (_BINARY_TARGET_NOTE,)


class CostSweepRow(EvaluationModel):
    threshold: str
    auto_accepted: int
    routed_to_review: int
    wrong_auto_accepts: int
    expected_cost_per_invoice: str | None


class CostSweepTable(EvaluationModel):
    rows: tuple[CostSweepRow, ...]
    lowest_cost_threshold: str | None
    review_cost: str
    error_cost: str
    sample_count: int
    kind: MetricKind = MetricKind.DECISION_SUPPORT
    disclaimer: str = _DECISION_SUPPORT_DISCLAIMER
    limitations: tuple[str, ...] = (_BINARY_TARGET_NOTE,)


def _participants(
    records: tuple[EvaluationRecord, ...],
) -> tuple[list[tuple[Decimal, bool]], int]:
    """(confidence, correct) pairs plus the excluded count.

    A record participates in calibration only when it has both a confidence
    value and a judgeable correctness; ``Decimal(str(x))`` keeps the exact
    decimal literal the caller supplied.
    """

    pairs: list[tuple[Decimal, bool]] = []
    excluded = 0
    for record in records:
        correct = invoice_is_correct(record)
        if record.model_reported_confidence is None or correct is None:
            excluded += 1
            continue
        pairs.append((Decimal(str(record.model_reported_confidence)), correct))
    return pairs, excluded


def brier_score(records: tuple[EvaluationRecord, ...]) -> MetricResult:
    """Mean squared gap between confidence and the binary target."""

    pairs, excluded = _participants(records)
    squared_sum = sum(
        (
            (confidence - (Decimal(1) if correct else Decimal(0))) ** 2
            for confidence, correct in pairs
        ),
        Decimal(0),
    )
    count = len(pairs)
    return MetricResult(
        metric_id="brier_score",
        kind=MetricKind.CALIBRATION,
        numerator=canonical_decimal_string(squared_sum),
        denominator=str(count),
        value=(
            canonical_decimal_string(squared_sum / count) if count else None
        ),
        sample_count=len(records),
        excluded_missing=excluded,
        sufficiency=(
            SufficiencyStatus.OK
            if count
            else SufficiencyStatus.INSUFFICIENT_EVIDENCE
        ),
        limitations=(_BINARY_TARGET_NOTE,),
    )


def _bin_index(confidence: Decimal) -> int:
    index = int((confidence * 10).to_integral_value(rounding=ROUND_FLOOR))
    return min(index, 9)


def calibration_bins(
    records: tuple[EvaluationRecord, ...],
) -> CalibrationTable:
    """Ten fixed-width bins; the last bin is right-closed [0.9, 1.0]."""

    pairs, excluded = _participants(records)
    grouped: dict[int, list[tuple[Decimal, bool]]] = {}
    for confidence, correct in pairs:
        grouped.setdefault(_bin_index(confidence), []).append(
            (confidence, correct)
        )
    bins: list[CalibrationBin] = []
    for index in range(10):
        members = grouped.get(index, [])
        count = len(members)
        if count:
            confidence_sum = sum(
                (confidence for confidence, _ in members), Decimal(0)
            )
            correct_count = sum(1 for _, correct in members if correct)
            mean_confidence = canonical_decimal_string(confidence_sum / count)
            observed_rate = canonical_decimal_string(
                Decimal(correct_count) / count
            )
        else:
            mean_confidence = None
            observed_rate = None
        bins.append(
            CalibrationBin(
                lower=canonical_decimal_string(Decimal(index) / 10),
                upper=canonical_decimal_string(Decimal(index + 1) / 10),
                count=count,
                mean_confidence=mean_confidence,
                observed_rate=observed_rate,
            )
        )
    return CalibrationTable(
        bins=tuple(bins),
        sample_count=len(pairs),
        excluded_missing=excluded,
        sufficiency=(
            SufficiencyStatus.OK
            if pairs
            else SufficiencyStatus.INSUFFICIENT_EVIDENCE
        ),
        limitations=(_BINARY_TARGET_NOTE,),
    )


def expected_calibration_error(
    records: tuple[EvaluationRecord, ...],
) -> MetricResult:
    """Count-weighted mean |observed rate - mean confidence| across bins."""

    pairs, excluded = _participants(records)
    total = len(pairs)
    grouped: dict[int, list[tuple[Decimal, bool]]] = {}
    for confidence, correct in pairs:
        grouped.setdefault(_bin_index(confidence), []).append(
            (confidence, correct)
        )
    weighted_gap_sum = Decimal(0)
    for members in grouped.values():
        count = len(members)
        confidence_sum = sum(
            (confidence for confidence, _ in members), Decimal(0)
        )
        correct_count = sum(1 for _, correct in members if correct)
        gap = abs(
            Decimal(correct_count) / count - confidence_sum / count
        )
        weighted_gap_sum += count * gap
    return MetricResult(
        metric_id="expected_calibration_error",
        kind=MetricKind.CALIBRATION,
        numerator=canonical_decimal_string(weighted_gap_sum),
        denominator=str(total),
        value=(
            canonical_decimal_string(weighted_gap_sum / total)
            if total
            else None
        ),
        sample_count=len(records),
        excluded_missing=excluded,
        sufficiency=(
            SufficiencyStatus.OK
            if total
            else SufficiencyStatus.INSUFFICIENT_EVIDENCE
        ),
        limitations=(_BINARY_TARGET_NOTE,),
    )


def selective_risk_table(
    records: tuple[EvaluationRecord, ...],
    thresholds: tuple[Decimal, ...] = DEFAULT_THRESHOLDS,
) -> SelectiveRiskTable:
    """Coverage versus match-rate per threshold.

    A record without a confidence value can never be auto-accepted, so it
    counts toward the denominator but is never covered.
    """

    judgeable = [
        (record.model_reported_confidence, invoice_is_correct(record))
        for record in records
    ]
    scored = [
        (Decimal(str(confidence)), bool(correct))
        for confidence, correct in judgeable
        if confidence is not None and correct is not None
    ]
    excluded = sum(1 for _, correct in judgeable if correct is None)
    total = len(records) - excluded
    rows: list[SelectiveRiskRow] = []
    for threshold in thresholds:
        covered = [
            correct for confidence, correct in scored if confidence >= threshold
        ]
        covered_count = len(covered)
        correct_count = sum(1 for correct in covered if correct)
        if covered_count:
            accuracy = canonical_decimal_string(
                Decimal(correct_count) / covered_count
            )
            risk = canonical_decimal_string(
                Decimal(covered_count - correct_count) / covered_count
            )
        else:
            accuracy = None
            risk = None
        rows.append(
            SelectiveRiskRow(
                threshold=canonical_decimal_string(threshold),
                covered=covered_count,
                coverage=(
                    canonical_decimal_string(Decimal(covered_count) / total)
                    if total
                    else None
                ),
                accuracy_on_covered=accuracy,
                risk_on_covered=risk,
            )
        )
    return SelectiveRiskTable(
        rows=tuple(rows),
        sample_count=total,
        excluded_missing=excluded,
    )


def threshold_cost_sweep(
    records: tuple[EvaluationRecord, ...],
    *,
    review_cost: Decimal,
    error_cost: Decimal,
    thresholds: tuple[Decimal, ...] = DEFAULT_THRESHOLDS,
) -> CostSweepTable:
    """Expected caller-priced cost per invoice at each threshold.

    Costs are caller-supplied business inputs; nothing here hard-codes a
    price. Records below threshold (or without confidence) route to review.
    """

    for label, value in (("review_cost", review_cost), ("error_cost", error_cost)):
        if not value.is_finite() or value < 0:
            raise ValueError(f"{label} must be a finite non-negative Decimal")

    scored: list[tuple[Decimal | None, bool | None, bool]] = [
        (
            (
                Decimal(str(record.model_reported_confidence))
                if record.model_reported_confidence is not None
                else None
            ),
            invoice_is_correct(record),
            bool(record.expected_fields)
            and all(
                name in record.predicted_fields for name in record.expected_fields
            ),
        )
        for record in records
    ]
    total = len(scored)
    rows: list[CostSweepRow] = []
    for threshold in thresholds:
        auto_accepted = 0
        wrong_auto_accepts = 0
        routed_to_review = 0
        for confidence, correct, decision_eligible in scored:
            if not decision_eligible:
                routed_to_review += 1
            elif confidence is not None and confidence >= threshold:
                auto_accepted += 1
                if correct is False:
                    wrong_auto_accepts += 1
            else:
                routed_to_review += 1
        if total:
            expected_cost = canonical_decimal_string(
                (
                    routed_to_review * review_cost
                    + wrong_auto_accepts * error_cost
                )
                / total
            )
        else:
            expected_cost = None
        rows.append(
            CostSweepRow(
                threshold=canonical_decimal_string(threshold),
                auto_accepted=auto_accepted,
                routed_to_review=routed_to_review,
                wrong_auto_accepts=wrong_auto_accepts,
                expected_cost_per_invoice=expected_cost,
            )
        )
    best: str | None = None
    best_cost: Decimal | None = None
    for row in rows:
        if row.expected_cost_per_invoice is None:
            continue
        cost = Decimal(row.expected_cost_per_invoice)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best = row.threshold
    return CostSweepTable(
        rows=tuple(rows),
        lowest_cost_threshold=best,
        review_cost=canonical_decimal_string(review_cost),
        error_cost=canonical_decimal_string(error_cost),
        sample_count=total,
    )
