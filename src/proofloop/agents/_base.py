"""Shared, cloud-neutral base types for the ProofLoop agent foundation.

This module is deliberately independent of `proofloop.domain`. Nothing here may
import the domain models, ports, or evaluator; the agent layer stays isolated
from the (still-changing) evidence contracts until a later integration review.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

# A non-empty, whitespace-trimmed string used for identifiers and short labels.
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# ISO-4217-style 3-letter currency code, upper-cased.
CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{3}$"),
]


def _strict_decimal(value: object) -> Decimal:
    """Coerce to ``Decimal`` while refusing binary floats for monetary values.

    Money and quantities must never originate from a binary ``float`` because
    ``0.1 + 0.2 != 0.3`` would silently corrupt reconciliation. Strings, ints,
    and ``Decimal`` are accepted; ``float`` and ``bool`` are rejected.
    """

    if isinstance(value, bool):
        raise ValueError("a boolean is not a valid monetary or quantity value")
    if isinstance(value, float):
        raise ValueError("use a string or Decimal for exact money, not a float")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation as error:
            raise ValueError(f"{value!r} is not a valid decimal") from error
    raise ValueError(f"unsupported numeric type: {type(value).__name__}")


# Exact decimal type for money and quantities; rejects binary floats.
ExactDecimal = Annotated[Decimal, BeforeValidator(_strict_decimal)]


def require_utc(value: datetime) -> datetime:
    """Reject naive or non-UTC timestamps at the agent boundary."""

    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC-aware")
    return value


class AgentModel(BaseModel):
    """Immutable, strict base for every agent-owned contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
