"""Versioned, PII-free, immutable evaluation records (schema 1.0.0).

Deliberately self-contained: these contracts import nothing from the runtime
packages, so the evaluation layer can never observe or influence live
compliance state. Field values are stored exactly as supplied (no silent
whitespace stripping) because the exact-match metric compares raw strings.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"

# A non-empty, whitespace-trimmed identifier or short label.
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Best-effort structural PII guard for stored field values. This is a refusal
# gate for obviously unsafe values (e-mail shapes, card/account-length digit
# runs), not a DLP guarantee; the documented policy is that callers must only
# supply synthetic, public, or de-identified values in the first place.
_EMAIL_SHAPE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_LONG_DIGIT_RUN = re.compile(r"\d{13,}")


class EvaluationModel(BaseModel):
    """Immutable, strict base for every evaluation contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DatasetProvenance(str, Enum):
    """Where the labeled records came from; controls what may be claimed."""

    SYNTHETIC = "SYNTHETIC"
    PUBLIC = "PUBLIC"
    DEIDENTIFIED_CUSTOMER = "DEIDENTIFIED_CUSTOMER"


class EvaluationSplit(str, Enum):
    """Development tunes, validation selects, holdout is reported once."""

    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    HOLDOUT = "HOLDOUT"


class DocumentTags(EvaluationModel):
    """Optional slicing tags; never customer identifiers."""

    difficulty: Identifier | None = None
    category: Identifier | None = None
    source: Identifier | None = None


def _reject_pii_shaped(fields: dict[str, str | None]) -> dict[str, str | None]:
    for name, value in fields.items():
        if value is None:
            continue
        compact = value.replace("-", "").replace(" ", "")
        if _EMAIL_SHAPE.search(value) or _LONG_DIGIT_RUN.search(compact):
            raise ValueError(
                f"field {name!r} looks like PII and was rejected; evaluation "
                "records must be PII-free"
            )
    return fields


class EvaluationRecord(EvaluationModel):
    """One labeled extraction outcome. PII-free by contract and by guard."""

    schema_version: Literal["1.0.0"]
    dataset_record_id: Identifier
    dataset_provenance: DatasetProvenance
    split: EvaluationSplit
    expected_fields: dict[str, str | None]
    predicted_fields: dict[str, str | None]
    model_reported_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provider_config_id: Identifier
    prompt_config_id: Identifier
    latency_ms: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    tags: DocumentTags = Field(default_factory=DocumentTags)
    run_id: Identifier | None = None

    _expected_pii_free = field_validator("expected_fields")(_reject_pii_shaped)
    _predicted_pii_free = field_validator("predicted_fields")(_reject_pii_shaped)


class EvaluationDataset(EvaluationModel):
    """An ordered set of records; refuses duplicates and split leakage."""

    schema_version: Literal["1.0.0"]
    records: tuple[EvaluationRecord, ...] = ()

    @model_validator(mode="after")
    def record_ids_must_be_unique_and_split_pure(self) -> Self:
        seen: dict[tuple[str, EvaluationSplit], int] = {}
        splits_by_id: dict[str, set[EvaluationSplit]] = {}
        for record in self.records:
            key = (record.dataset_record_id, record.split)
            seen[key] = seen.get(key, 0) + 1
            splits_by_id.setdefault(record.dataset_record_id, set()).add(
                record.split
            )
        duplicates = sorted(
            record_id for (record_id, _), count in seen.items() if count > 1
        )
        if duplicates:
            raise ValueError(
                f"duplicate dataset_record_id within one split: {duplicates}"
            )
        leaked = sorted(
            record_id
            for record_id, splits in splits_by_id.items()
            if len(splits) > 1
        )
        if leaked:
            raise ValueError(
                "split leakage: the same dataset_record_id appears in more "
                f"than one split: {leaked}"
            )
        return self
