"""Report tests: sufficiency, claim boundaries, split misuse, determinism."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from proofloop.evaluation.records import DatasetProvenance, EvaluationSplit
from proofloop.evaluation.report import (
    PricingConfig,
    ReportConfig,
    build_report,
    report_to_json,
    report_to_markdown,
)
from .eval_fixtures import make_dataset, make_record


def _config(**overrides):  # type: ignore[no-untyped-def]
    payload: dict = {
        "tuning_split": EvaluationSplit.DEVELOPMENT,
        "report_split": EvaluationSplit.HOLDOUT,
    }
    payload.update(overrides)
    return ReportConfig(**payload)


def _mixed_dataset():  # type: ignore[no-untyped-def]
    return make_dataset(
        make_record(dataset_record_id="d1"),
        make_record(dataset_record_id="d2", model_reported_confidence=0.4),
        make_record(
            dataset_record_id="h1",
            split=EvaluationSplit.HOLDOUT,
            dataset_provenance=DatasetProvenance.DEIDENTIFIED_CUSTOMER,
        ),
    )


def test_empty_dataset_returns_insufficient_evidence_and_no_metrics() -> None:
    report = build_report(make_dataset(), _config())
    assert report.status == "INSUFFICIENT_EVIDENCE"
    assert report.splits == ()


def test_wholly_unjudgeable_dataset_has_no_supported_conclusion() -> None:
    dataset = make_dataset(make_record(expected_fields={}, predicted_fields={}))
    report = build_report(dataset, _config())
    assert report.status == "INSUFFICIENT_EVIDENCE"
    assert report.supported_claims == ()


def test_all_synthetic_data_blocks_production_accuracy_claims() -> None:
    dataset = make_dataset(make_record())
    report = build_report(dataset, _config())
    assert report.claim_boundary == "SYNTHETIC_ONLY"
    assert any(
        "production" in claim.lower() for claim in report.unsupported_claims
    )
    # Synthetic labels verify the harness; they are not accuracy evidence.
    assert not any(
        "accuracy" in claim.lower() for claim in report.supported_claims
    )


def test_tuning_and_reporting_on_the_same_split_is_flagged_as_misuse() -> None:
    dataset = make_dataset(make_record())
    report = build_report(
        dataset,
        _config(
            tuning_split=EvaluationSplit.DEVELOPMENT,
            report_split=EvaluationSplit.DEVELOPMENT,
        ),
    )
    assert report.split_misuse is True
    assert any("same split" in claim.lower() for claim in report.unsupported_claims)


def test_distinct_tuning_and_report_splits_are_not_misuse() -> None:
    report = build_report(_mixed_dataset(), _config())
    assert report.split_misuse is False


def test_report_json_is_byte_identical_for_identical_input() -> None:
    dataset = _mixed_dataset()
    first = report_to_json(build_report(dataset, _config()))
    second = report_to_json(build_report(dataset, _config()))
    assert first == second


def test_run_id_is_the_only_nondeterministic_field() -> None:
    dataset = _mixed_dataset()
    with_run_a = json.loads(
        report_to_json(build_report(dataset, _config(run_id="run-a")))
    )
    with_run_b = json.loads(
        report_to_json(build_report(dataset, _config(run_id="run-b")))
    )
    assert with_run_a["run_metadata"] != with_run_b["run_metadata"]
    with_run_a.pop("run_metadata")
    with_run_b.pop("run_metadata")
    assert with_run_a == with_run_b


def test_markdown_and_json_come_from_the_same_data() -> None:
    dataset = _mixed_dataset()
    report = build_report(dataset, _config())
    markdown = report_to_markdown(report)
    assert "INSUFFICIENT" not in markdown or report.status != "OK"
    assert "GREEN" not in markdown  # never speaks in runtime verdict vocabulary
    assert "brier" in markdown.lower()


def test_pricing_absent_omits_cost_estimates_entirely() -> None:
    report = build_report(_mixed_dataset(), _config())
    assert report.estimated_cost is None


def test_pricing_present_adds_caller_priced_cost_estimates() -> None:
    pricing = PricingConfig(
        input_token_price_per_1k="3.00",
        output_token_price_per_1k="15.00",
        currency="USD",
    )
    report = build_report(_mixed_dataset(), _config(pricing=pricing))
    assert report.estimated_cost is not None
    assert report.estimated_cost.currency == "USD"
    # 3 records x (800 in + 150 out): in 2400 tokens -> 7.2, out 450 -> 6.75
    assert report.estimated_cost.total == "13.95"


def test_report_separates_computed_values_from_conclusions() -> None:
    report = build_report(_mixed_dataset(), _config())
    assert report.supported_claims  # says what WAS computed
    assert report.unsupported_claims  # says what may NOT be concluded
    assert any("verdict" in c.lower() for c in report.unsupported_claims)


def test_cost_sweep_requires_caller_costs_and_is_omitted_without_them() -> None:
    report = build_report(_mixed_dataset(), _config())
    assert report.threshold_sweep is None
    with_costs = build_report(
        _mixed_dataset(),
        _config(review_cost=Decimal("1"), error_cost=Decimal("10")),
    )
    assert with_costs.threshold_sweep is not None


@pytest.mark.parametrize("invalid", ("-1", "NaN", "Infinity", "-Infinity"))
def test_report_config_rejects_negative_or_non_finite_costs(invalid: str) -> None:
    with pytest.raises(ValidationError, match="finite|greater than or equal"):
        _config(review_cost=Decimal(invalid), error_cost=Decimal("1"))
    with pytest.raises(ValidationError, match="finite|greater than or equal"):
        _config(review_cost=Decimal("1"), error_cost=Decimal(invalid))


@pytest.mark.parametrize("invalid", ("-1", "NaN", "Infinity", "-Infinity"))
def test_pricing_rejects_negative_or_non_finite_values(invalid: str) -> None:
    with pytest.raises(ValidationError, match="finite non-negative"):
        PricingConfig(
            input_token_price_per_1k=invalid,
            output_token_price_per_1k="1",
            currency="USD",
        )
    with pytest.raises(ValidationError, match="finite non-negative"):
        PricingConfig(
            input_token_price_per_1k="1",
            output_token_price_per_1k=invalid,
            currency="USD",
        )
