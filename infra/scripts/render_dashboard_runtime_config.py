#!/usr/bin/env python3
"""Render the public dashboard runtime configuration without secrets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit


def render_runtime_config(
    api_base_url: str, output: Path, demo_api_key: str | None = None
) -> None:
    """Write one HTTPS API origin to a deterministic JavaScript assignment.

    An optional read-only demo API key may be embedded so evaluators can load a
    protected record with one click. The dashboard uses it only as a default
    field value: an operator-entered key in session storage always wins, and the
    "Clear saved key" control still empties the field.
    """

    parsed = urlsplit(api_base_url)
    invalid = (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or bool(parsed.query)
        or bool(parsed.fragment)
    )
    if invalid:
        raise ValueError("API base URL must be one HTTPS origin without credentials or a path")
    origin = f"https://{parsed.netloc}"
    config: dict[str, str] = {"apiBaseUrl": origin}
    if demo_api_key:
        config["demoApiKey"] = demo_api_key
    payload = json.dumps(config, separators=(",", ":"))
    output.write_text(
        f"window.PROOFLOOP_RUNTIME_CONFIG = Object.freeze({payload});\n",
        encoding="utf-8",
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api_base_url")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--demo-api-key",
        default=None,
        help="Optional read-only demo key embedded as the dashboard's default key value.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        render_runtime_config(args.api_base_url, args.output, args.demo_api_key)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
