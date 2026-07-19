#!/usr/bin/env python3
"""Render the public dashboard runtime configuration without secrets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit


def render_runtime_config(api_base_url: str, output: Path) -> None:
    """Write one HTTPS API origin to a deterministic JavaScript assignment."""

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
    payload = json.dumps({"apiBaseUrl": origin}, separators=(",", ":"))
    output.write_text(
        f"window.PROOFLOOP_RUNTIME_CONFIG = Object.freeze({payload});\n",
        encoding="utf-8",
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api_base_url")
    parser.add_argument("output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        render_runtime_config(args.api_base_url, args.output)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
