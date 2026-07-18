"""Offline data-science evaluation layer for ProofLoop invoice extraction.

This package is analytical support only. It reads versioned, PII-free
evaluation records and produces deterministic JSON/Markdown reports. It never
creates, modifies, overrides, or suppresses a runtime compliance verdict,
never approves an invoice or releases a payment, never bypasses the
human-review boundary, and never touches evidence freshness. It imports only
the Python standard library and Pydantic — no other ProofLoop package and no
cloud SDK.
"""

from proofloop.evaluation.records import (
    DatasetProvenance,
    EvaluationDataset,
    EvaluationRecord,
    EvaluationSplit,
)
from proofloop.evaluation.report import (
    EvaluationReport,
    PricingConfig,
    ReportConfig,
    build_report,
    report_to_json,
    report_to_markdown,
)

__all__ = [
    "DatasetProvenance",
    "EvaluationDataset",
    "EvaluationRecord",
    "EvaluationSplit",
    "EvaluationReport",
    "PricingConfig",
    "ReportConfig",
    "build_report",
    "report_to_json",
    "report_to_markdown",
]
