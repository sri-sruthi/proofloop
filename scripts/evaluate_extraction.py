"""Offline extraction-evaluation CLI.

Reads a versioned evaluation-record dataset, validates it fully before any
computation, and writes deterministic JSON and Markdown reports. Runs
entirely offline: no cloud SDK, no network, no runtime evidence, and no
compliance state is ever read or written.

Usage:
    python scripts/evaluate_extraction.py dataset.json \
        --json-out report.json --markdown-out report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import ValidationError

from proofloop.evaluation.records import EvaluationDataset, EvaluationSplit
from proofloop.evaluation.report import (
    PricingConfig,
    ReportConfig,
    build_report,
    report_to_json,
    report_to_markdown,
)

_SPLIT_CHOICES = [split.value for split in EvaluationSplit]


class SafeCliError(Exception):
    """A user-facing input problem with a one-line explanation."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evaluate_extraction",
        description=(
            "Offline, deterministic evaluation of invoice-extraction "
            "records. Analytical support only; never a runtime authority."
        ),
    )
    parser.add_argument("dataset", help="path to the evaluation dataset JSON")
    parser.add_argument("--json-out", help="write the JSON report here")
    parser.add_argument("--markdown-out", help="write the Markdown report here")
    parser.add_argument(
        "--tuning-split",
        choices=_SPLIT_CHOICES,
        default=EvaluationSplit.DEVELOPMENT.value,
        help="split used for threshold tuning",
    )
    parser.add_argument(
        "--report-split",
        choices=_SPLIT_CHOICES,
        default=EvaluationSplit.HOLDOUT.value,
        help="split final performance would be reported on",
    )
    parser.add_argument(
        "--review-cost",
        help="caller-supplied cost of routing one invoice to human review",
    )
    parser.add_argument(
        "--error-cost",
        help="caller-supplied cost of one wrong auto-accepted invoice",
    )
    parser.add_argument(
        "--input-token-price-per-1k",
        help="caller-supplied input token price per 1000 tokens",
    )
    parser.add_argument(
        "--output-token-price-per-1k",
        help="caller-supplied output token price per 1000 tokens",
    )
    parser.add_argument(
        "--price-currency",
        help="currency label for the caller-supplied prices",
    )
    parser.add_argument(
        "--run-id",
        help="optional run identifier recorded as run metadata",
    )
    return parser


def _parse_decimal(raw: str, flag: str) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation as error:
        raise SafeCliError(f"{flag} must be a decimal number, got {raw!r}") from error


def _load_dataset(path_text: str) -> EvaluationDataset:
    path = Path(path_text)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SafeCliError(f"cannot read dataset file {path}: {error}") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SafeCliError(f"dataset file {path} is not valid JSON: {error}") from error
    try:
        return EvaluationDataset.model_validate(payload)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        raise SafeCliError(
            f"dataset validation failed at {location or 'root'}: {first['msg']}"
        ) from error


def _build_config(args: argparse.Namespace) -> ReportConfig:
    review_cost = error_cost = None
    if (args.review_cost is None) != (args.error_cost is None):
        raise SafeCliError(
            "--review-cost and --error-cost must be supplied together"
        )
    if args.review_cost is not None:
        review_cost = _parse_decimal(args.review_cost, "--review-cost")
        error_cost = _parse_decimal(args.error_cost, "--error-cost")

    pricing = None
    prices = (args.input_token_price_per_1k, args.output_token_price_per_1k)
    if any(price is not None for price in prices):
        if any(price is None for price in prices):
            raise SafeCliError(
                "--input-token-price-per-1k and --output-token-price-per-1k "
                "must be supplied together"
            )
        try:
            pricing = PricingConfig(
                input_token_price_per_1k=args.input_token_price_per_1k,
                output_token_price_per_1k=args.output_token_price_per_1k,
                currency=args.price_currency or "UNSPECIFIED",
            )
        except ValidationError as error:
            message = error.errors()[0]["msg"]
            raise SafeCliError(f"invalid pricing: {message}") from error

    return ReportConfig(
        tuning_split=EvaluationSplit(args.tuning_split),
        report_split=EvaluationSplit(args.report_split),
        review_cost=review_cost,
        error_cost=error_cost,
        pricing=pricing,
        run_id=args.run_id,
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        dataset = _load_dataset(args.dataset)
        config = _build_config(args)
    except SafeCliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    report = build_report(dataset, config)
    json_text = report_to_json(report)
    markdown_text = report_to_markdown(report)

    if args.json_out:
        Path(args.json_out).write_text(json_text, encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown_text, encoding="utf-8")
    if not args.json_out and not args.markdown_out:
        sys.stdout.write(json_text)
    else:
        print(
            f"evaluation complete: status={report.status} "
            f"claim_boundary={report.claim_boundary}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
