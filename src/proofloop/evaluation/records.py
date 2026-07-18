"""Versioned, PII-free, immutable evaluation records (schema 1.0.0).

Deliberately self-contained: these contracts import nothing from the runtime
packages, so the evaluation layer can never observe or influence live
compliance state. Field values are stored exactly as supplied (no silent
whitespace stripping) because the exact-match metric compares raw strings.
"""

from __future__ import annotations

import re
from enum import Enum
from types import MappingProxyType
from typing import Annotated, Literal, Mapping, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"

INVOICE_SCALAR_FIELDS_V1 = frozenset(
    {
        "currency",
        "document_id",
        "invoice_date",
        "invoice_number",
        "line_total",
        "po_number",
        "quantity",
        "status",
        "subtotal",
        "tax",
        "total",
        "unit_price",
        "vendor_id",
        "vendor_name",
    }
)

# A non-empty, bounded, whitespace-trimmed identifier or short label.
Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]

# Conservative refusal gates for structurally unsafe evaluation content. These
# are a bounded offline-record contract, not an enterprise DLP replacement.
_EMAIL_SHAPE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_AWS_ACCESS_KEY_SHAPE = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
_BEARER_TOKEN_SHAPE = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.I)
_PRIVATE_KEY_HEADER = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
_PROMPT_ROLE_MARKER = re.compile(
    r"(?:ignore\s+(?:all\s+)?previous\s+instructions|<\|(?:system|user|assistant)\|>)",
    re.I,
)
_IDENTIFIER_LIKE_FIELDS = frozenset(
    {"document_id", "invoice_number", "po_number", "vendor_id"}
)
_MAX_SCALAR_LENGTH = 256


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

    @field_validator("difficulty", "category", "source")
    @classmethod
    def tag_values_must_be_safe(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_safe_text(value, context="tag")
        return value


def _looks_like_phone(value: str) -> bool:
    digits = sum(character.isdigit() for character in value)
    return digits >= 10 and any(character in value for character in "+() ")


def _validate_safe_text(
    value: str,
    *,
    context: str,
    allow_identifier_shape: bool = False,
) -> None:
    if len(value) > _MAX_SCALAR_LENGTH:
        raise ValueError(
            f"{context} exceeds the bounded {_MAX_SCALAR_LENGTH}-character limit"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{context} contains unsafe control or multiline content")
    if _EMAIL_SHAPE.search(value):
        raise ValueError(f"{context} looks like PII and was rejected")
    if not allow_identifier_shape and _looks_like_phone(value):
        raise ValueError(f"{context} looks like phone-number PII and was rejected")
    if (
        _AWS_ACCESS_KEY_SHAPE.search(value)
        or _BEARER_TOKEN_SHAPE.search(value)
        or _PRIVATE_KEY_HEADER.search(value)
        or _PROMPT_ROLE_MARKER.search(value)
    ):
        raise ValueError(f"{context} contains unsafe credential or prompt content")


def _validate_and_freeze_fields(
    fields: Mapping[str, str | None],
) -> Mapping[str, str | None]:
    for name, value in fields.items():
        if name not in INVOICE_SCALAR_FIELDS_V1:
            raise ValueError(
                f"field {name!r} is not an allowed invoice scalar in schema 1.0.0"
            )
        if value is None:
            continue
        _validate_safe_text(
            value,
            context=f"field {name!r}",
            allow_identifier_shape=name in _IDENTIFIER_LIKE_FIELDS,
        )
    return MappingProxyType(dict(fields))


class EvaluationRecord(EvaluationModel):
    """One labeled extraction outcome. PII-free by contract and by guard."""

    schema_version: Literal["1.0.0"]
    dataset_record_id: Identifier
    dataset_provenance: DatasetProvenance
    split: EvaluationSplit
    expected_fields: Mapping[str, str | None]
    predicted_fields: Mapping[str, str | None]
    model_reported_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provider_config_id: Identifier
    prompt_config_id: Identifier
    latency_ms: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    tags: DocumentTags = Field(default_factory=DocumentTags)
    run_id: Identifier | None = None

    _expected_fields_safe = field_validator("expected_fields")(
        _validate_and_freeze_fields
    )
    _predicted_fields_safe = field_validator("predicted_fields")(
        _validate_and_freeze_fields
    )

    @field_validator(
        "dataset_record_id",
        "provider_config_id",
        "prompt_config_id",
        "run_id",
    )
    @classmethod
    def metadata_values_must_be_safe(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_safe_text(
                value,
                context="evaluation metadata",
                allow_identifier_shape=True,
            )
        return value

    @field_serializer("expected_fields", "predicted_fields")
    def serialize_field_mapping(
        self, value: Mapping[str, str | None]
    ) -> dict[str, str | None]:
        return dict(value)


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
