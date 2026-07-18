"""Conservative, documented normalization policy for match metrics.

Text: NFKC unicode normalization, whitespace-run collapse, casefold. Nothing
more — no punctuation stripping, no transliteration, so genuinely different
invoice values can never be made to look equal.

Numbers: only plain decimal strings parse (optional sign, digits, at most one
decimal point). Currency symbols and thousands separators are refused rather
than stripped, because "1,234" versus "1.234" is locale-ambiguous and a wrong
guess could hide a real financial-harm error. Unparseable values are excluded
and counted, never guessed.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_EVEN, Decimal

# Money/quantity fields compared numerically instead of as strings.
NUMERIC_FIELD_NAMES = frozenset(
    {"total", "subtotal", "tax", "quantity", "unit_price", "line_total"}
)

_PLAIN_DECIMAL = re.compile(r"^[+-]?\d+(\.\d+)?$")
_TWELVE_PLACES = Decimal("1E-12")


def normalize_text(value: str) -> str:
    """NFKC -> collapse whitespace runs to one space -> strip -> casefold."""

    folded = unicodedata.normalize("NFKC", value)
    collapsed = " ".join(folded.split())
    return collapsed.casefold()


def parse_amount(value: str | None) -> Decimal | None:
    """Parse a plain decimal string exactly; anything else is None."""

    if value is None:
        return None
    stripped = value.strip()
    if not _PLAIN_DECIMAL.match(stripped):
        return None
    return Decimal(stripped)


def canonical_decimal_string(value: Decimal) -> str:
    """Fixed-point string, 12-decimal-place half-even, trailing zeros removed.

    One canonical formatter keeps every serialized number byte-stable across
    runs, which the deterministic-output contract depends on.
    """

    quantized = value.quantize(_TWELVE_PLACES, rounding=ROUND_HALF_EVEN)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text
