#!/usr/bin/env python3
"""Copy the ProofLoop runtime package into a Lambda artifact directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Sequence


def copy_runtime_package(source: Path, destination: Path) -> None:
    source = source.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {
            name
            for name in names
            if name == "__pycache__" or name.endswith((".pyc", ".pyo"))
        }
        if Path(directory).resolve() == source:
            ignored.add("evaluation")
        return ignored

    shutil.copytree(source, destination, ignore=ignore)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    copy_runtime_package(args.source, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
