"""Deterministic evaluation report: JSON for machines, Markdown for humans.

The report separates computed values from conclusions the evidence does or
does not support. It never speaks in runtime verdict vocabulary, because its
output must not even be mistakable for a compliance state.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from pydantic import field_validator

from proofloop.evaluation.calibration import (
    CalibrationTable,
    CostSweepTable,
    SelectiveRiskTable,
    brier_score,
    calibration_bins,
    expected_calibration_error,
    selective_risk_table,
    threshold_cost_sweep,
)
from proofloop.evaluation.metrics import (
    LatencySummary,
    MetricResult,
    SufficiencyStatus,
    TokenSummary,
    field_match_results,
    invoice_exact_match,
    latency_summary,
    numeric_error_results,
    schema_valid_rate,
    token_summary,
)
from proofloop.evaluation.normalization import canonical_decimal_string
from proofloop.evaluation.records import (
    DatasetProvenance,
    EvaluationDataset,
    EvaluationModel,
    EvaluationRecord,
    EvaluationSplit,
)

_SPLIT_ORDER = (
    EvaluationSplit.DEVELOPMENT,
    EvaluationSplit.VALIDATION,
    EvaluationSplit.HOLDOUT,
)

_COST_DISCLAIMER = (
    "Estimated from caller-supplied token prices; no price is hard-coded and "
    "no billing system was consulted."
)


def _parse_price(value: str) -> str:
    try:
        Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{value!r} is not a valid decimal price") from error
    return value


class PricingConfig(EvaluationModel):
    """Caller-supplied token pricing; never bundled with the harness."""

    input_token_price_per_1k: str
    output_token_price_per_1k: str
    currency: str

    _input_price_valid = field_validator("input_token_price_per_1k")(
        _parse_price
    )
    _output_price_valid = field_validator("output_token_price_per_1k")(
        _parse_price
    )


class ReportConfig(EvaluationModel):
    """How to evaluate: splits, optional business costs, optional pricing."""

    tuning_split: EvaluationSplit = EvaluationSplit.DEVELOPMENT
    report_split: EvaluationSplit = EvaluationSplit.HOLDOUT
    review_cost: Decimal | None = None
    error_cost: Decimal | None = None
    pricing: PricingConfig | None = None
    run_id: str | None = None


class EstimatedCost(EvaluationModel):
    currency: str
    input_tokens_total: str | None
    output_tokens_total: str | None
    input_cost: str | None
    output_cost: str | None
    total: str | None
    records_missing_tokens: int
    disclaimer: str = _COST_DISCLAIMER


class CategoryBreakdown(EvaluationModel):
    category: str
    invoice_match: MetricResult


class SplitSection(EvaluationModel):
    """Everything computed for one split."""

    split: EvaluationSplit
    record_count: int
    provenance_counts: dict[str, int]
    metrics: tuple[MetricResult, ...]
    calibration: CalibrationTable
    selective_risk: SelectiveRiskTable
    latency: LatencySummary
    tokens: TokenSummary
    by_category: tuple[CategoryBreakdown, ...]


class EvaluationReport(EvaluationModel):
    status: str
    claim_boundary: str
    split_misuse: bool
    splits: tuple[SplitSection, ...]
    threshold_sweep: CostSweepTable | None
    estimated_cost: EstimatedCost | None
    supported_claims: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    run_metadata: dict[str, str | None]


def _split_section(
    split: EvaluationSplit, records: tuple[EvaluationRecord, ...]
) -> SplitSection:
    provenance_counts: dict[str, int] = {}
    for record in records:
        provenance_counts[record.dataset_provenance.value] = (
            provenance_counts.get(record.dataset_provenance.value, 0) + 1
        )
    metrics: tuple[MetricResult, ...] = (
        *field_match_results(records, normalized=False),
        *field_match_results(records, normalized=True),
        invoice_exact_match(records),
        *numeric_error_results(records),
        schema_valid_rate(records),
        brier_score(records),
        expected_calibration_error(records),
    )
    categories = sorted(
        {record.tags.category or "untagged" for record in records}
    )
    by_category = tuple(
        CategoryBreakdown(
            category=category,
            invoice_match=invoice_exact_match(
                tuple(
                    record
                    for record in records
                    if (record.tags.category or "untagged") == category
                )
            ),
        )
        for category in categories
    )
    return SplitSection(
        split=split,
        record_count=len(records),
        provenance_counts=provenance_counts,
        metrics=metrics,
        calibration=calibration_bins(records),
        selective_risk=selective_risk_table(records),
        latency=latency_summary(records),
        tokens=token_summary(records),
        by_category=by_category,
    )


def _estimated_cost(
    records: tuple[EvaluationRecord, ...], pricing: PricingConfig
) -> EstimatedCost:
    input_price = Decimal(pricing.input_token_price_per_1k)
    output_price = Decimal(pricing.output_token_price_per_1k)
    input_tokens = [
        record.input_tokens
        for record in records
        if record.input_tokens is not None
    ]
    output_tokens = [
        record.output_tokens
        for record in records
        if record.output_tokens is not None
    ]
    missing = sum(
        1
        for record in records
        if record.input_tokens is None or record.output_tokens is None
    )
    input_total = sum(input_tokens) if input_tokens else None
    output_total = sum(output_tokens) if output_tokens else None
    input_cost = (
        Decimal(input_total) / 1000 * input_price
        if input_total is not None
        else None
    )
    output_cost = (
        Decimal(output_total) / 1000 * output_price
        if output_total is not None
        else None
    )
    total = (
        input_cost + output_cost
        if input_cost is not None and output_cost is not None
        else input_cost if input_cost is not None else output_cost
    )
    return EstimatedCost(
        currency=pricing.currency,
        input_tokens_total=(
            str(input_total) if input_total is not None else None
        ),
        output_tokens_total=(
            str(output_total) if output_total is not None else None
        ),
        input_cost=(
            canonical_decimal_string(input_cost)
            if input_cost is not None
            else None
        ),
        output_cost=(
            canonical_decimal_string(output_cost)
            if output_cost is not None
            else None
        ),
        total=canonical_decimal_string(total) if total is not None else None,
        records_missing_tokens=missing,
    )


def build_report(
    dataset: EvaluationDataset, config: ReportConfig
) -> EvaluationReport:
    records = dataset.records
    split_misuse = config.tuning_split == config.report_split

    provenances = {record.dataset_provenance for record in records}
    if not records:
        claim_boundary = "NO_DATA"
    elif provenances == {DatasetProvenance.SYNTHETIC}:
        claim_boundary = "SYNTHETIC_ONLY"
    elif DatasetProvenance.SYNTHETIC in provenances:
        claim_boundary = "MIXED_PROVENANCE"
    else:
        claim_boundary = "NON_SYNTHETIC"

    sections = tuple(
        _split_section(
            split,
            tuple(record for record in records if record.split is split),
        )
        for split in _SPLIT_ORDER
        if any(record.split is split for record in records)
    )

    threshold_sweep: CostSweepTable | None = None
    if config.review_cost is not None and config.error_cost is not None:
        tuning_records = tuple(
            record for record in records if record.split is config.tuning_split
        )
        threshold_sweep = threshold_cost_sweep(
            tuning_records,
            review_cost=config.review_cost,
            error_cost=config.error_cost,
        )

    estimated_cost = (
        _estimated_cost(records, config.pricing)
        if config.pricing is not None and records
        else None
    )

    supported: list[str] = []
    unsupported: list[str] = [
        "Nothing in this report creates, modifies, overrides, or suppresses "
        "a runtime compliance verdict, invoice disposition, or human-review "
        "boundary.",
        "No model-superiority conclusion is supported by a single smoke "
        "request or by this offline dataset alone.",
    ]
    if records:
        supported.append(
            f"Deterministic metrics were computed over {len(records)} "
            "record(s); identical ordered records and configuration "
            "reproduce identical output."
        )
        supported.append(
            "Sample sizes are reported exactly; no minimum-sample claim is "
            "made or implied."
        )
    if claim_boundary == "SYNTHETIC_ONLY":
        unsupported.append(
            "Synthetic fixtures verify the evaluation harness only; no "
            "production accuracy or calibration claim is supported."
        )
    if split_misuse:
        unsupported.append(
            "Threshold tuning and final reporting reference the same split; "
            "any tuned-threshold performance number from this configuration "
            "is withheld."
        )

    return EvaluationReport(
        status="OK" if records else "INSUFFICIENT_EVIDENCE",
        claim_boundary=claim_boundary,
        split_misuse=split_misuse,
        splits=sections,
        threshold_sweep=threshold_sweep,
        estimated_cost=estimated_cost,
        supported_claims=tuple(supported),
        unsupported_claims=tuple(unsupported),
        run_metadata={"run_id": config.run_id},
    )


def report_to_json(report: EvaluationReport) -> str:
    """Byte-stable JSON: sorted keys, fixed indentation, trailing newline."""

    payload = report.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _value_or_na(value: str | None) -> str:
    return value if value is not None else "n/a"


def report_to_markdown(report: EvaluationReport) -> str:
    """Human view of exactly the same data as the JSON output."""

    lines: list[str] = [
        "# ProofLoop Offline Extraction Evaluation",
        "",
        f"- Status: {report.status}",
        f"- Claim boundary: {report.claim_boundary}",
        f"- Split misuse: {'yes' if report.split_misuse else 'no'}",
        f"- Run id: {report.run_metadata.get('run_id') or 'n/a'}",
        "",
    ]
    for section in report.splits:
        lines.append(f"## Split: {section.split.value}")
        lines.append("")
        lines.append(f"- Records: {section.record_count}")
        provenance = ", ".join(
            f"{name}={count}"
            for name, count in sorted(section.provenance_counts.items())
        )
        lines.append(f"- Provenance: {provenance}")
        lines.append("")
        lines.append("| metric | value | numerator | denominator | excluded |")
        lines.append("|---|---|---|---|---|")
        for metric in section.metrics:
            excluded = metric.excluded_missing + metric.excluded_zero_denominator
            note = (
                ""
                if metric.sufficiency is SufficiencyStatus.OK
                else f" ({metric.sufficiency.value})"
            )
            lines.append(
                f"| {metric.metric_id} | {_value_or_na(metric.value)}{note} | "
                f"{metric.numerator} | {metric.denominator} | {excluded} |"
            )
        lines.append("")
        lines.append("### Selective risk (decision support)")
        lines.append("")
        lines.append("| threshold | covered | coverage | match rate | risk |")
        lines.append("|---|---|---|---|---|")
        for row in section.selective_risk.rows:
            lines.append(
                f"| {row.threshold} | {row.covered} | "
                f"{_value_or_na(row.coverage)} | "
                f"{_value_or_na(row.accuracy_on_covered)} | "
                f"{_value_or_na(row.risk_on_covered)} |"
            )
        lines.append("")
        lines.append(
            f"- Latency ms (n={section.latency.sample_count}): "
            f"min {_value_or_na(section.latency.minimum)}, "
            f"median {_value_or_na(section.latency.median)}, "
            f"mean {_value_or_na(section.latency.mean)}, "
            f"p95 {_value_or_na(section.latency.p95)}, "
            f"max {_value_or_na(section.latency.maximum)}"
        )
        lines.append(
            f"- Tokens: input total {_value_or_na(section.tokens.input_total)} "
            f"(missing {section.tokens.input_missing}), output total "
            f"{_value_or_na(section.tokens.output_total)} "
            f"(missing {section.tokens.output_missing})"
        )
        lines.append("")
    if report.threshold_sweep is not None:
        sweep = report.threshold_sweep
        lines.append("## Cost-sensitive threshold sweep (decision support)")
        lines.append("")
        lines.append(
            f"- Caller-supplied costs: review {sweep.review_cost}, "
            f"error {sweep.error_cost}"
        )
        lines.append(
            "| threshold | auto-accepted | to review | wrong accepts | "
            "expected cost/invoice |"
        )
        lines.append("|---|---|---|---|---|")
        for sweep_row in sweep.rows:
            lines.append(
                f"| {sweep_row.threshold} | {sweep_row.auto_accepted} | "
                f"{sweep_row.routed_to_review} | {sweep_row.wrong_auto_accepts} | "
                f"{_value_or_na(sweep_row.expected_cost_per_invoice)} |"
            )
        lines.append(
            f"- Lowest-cost threshold on the tuning split: "
            f"{_value_or_na(sweep.lowest_cost_threshold)}"
        )
        lines.append(f"- {sweep.disclaimer}")
        lines.append("")
    if report.estimated_cost is not None:
        cost = report.estimated_cost
        lines.append("## Estimated model cost (caller-supplied prices)")
        lines.append("")
        lines.append(
            f"- Input: {_value_or_na(cost.input_cost)} {cost.currency}; "
            f"output: {_value_or_na(cost.output_cost)} {cost.currency}; "
            f"total: {_value_or_na(cost.total)} {cost.currency}"
        )
        lines.append(f"- {cost.disclaimer}")
        lines.append("")
    lines.append("## Supported claims")
    lines.append("")
    lines.extend(f"- {claim}" for claim in report.supported_claims)
    lines.append("")
    lines.append("## Not supported by this evidence")
    lines.append("")
    lines.extend(f"- {claim}" for claim in report.unsupported_claims)
    lines.append("")
    return "\n".join(lines)
