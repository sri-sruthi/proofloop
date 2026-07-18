"""Shared builders for evaluation-layer tests. Synthetic, PII-free data only."""

from __future__ import annotations

from typing import Any, Final

from proofloop.evaluation.records import (
    DatasetProvenance,
    EvaluationDataset,
    EvaluationRecord,
    EvaluationSplit,
)

SCHEMA_VERSION: Final = "1.0.0"


def make_record(**overrides: Any) -> EvaluationRecord:
    """One valid synthetic evaluation record; override any field."""

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "dataset_record_id": "rec-001",
        "dataset_provenance": DatasetProvenance.SYNTHETIC,
        "split": EvaluationSplit.DEVELOPMENT,
        "expected_fields": {
            "invoice_number": "INV-1001",
            "vendor_name": "Acme GmbH",
            "total": "100.00",
        },
        "predicted_fields": {
            "invoice_number": "INV-1001",
            "vendor_name": "Acme GmbH",
            "total": "100.00",
        },
        "model_reported_confidence": 0.9,
        "provider_config_id": "stub-provider-v1",
        "prompt_config_id": "invoice-extraction-v1",
        "latency_ms": 1200,
        "input_tokens": 800,
        "output_tokens": 150,
    }
    payload.update(overrides)
    return EvaluationRecord(**payload)


def make_dataset(*records: EvaluationRecord) -> EvaluationDataset:
    return EvaluationDataset(schema_version=SCHEMA_VERSION, records=tuple(records))
