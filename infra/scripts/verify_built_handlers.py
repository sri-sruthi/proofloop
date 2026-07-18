#!/usr/bin/env python3
"""Import Lambda handlers strictly from SAM build artifact directories."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from typing import Sequence


def _clear_proofloop_modules() -> None:
    for name in tuple(sys.modules):
        if name == "proofloop" or name.startswith("proofloop."):
            del sys.modules[name]


def _inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def verify_handler(artifact: Path, handler_spec: str) -> None:
    artifact = artifact.resolve()
    if not artifact.is_dir():
        raise RuntimeError(f"Lambda build artifact is missing: {artifact}")
    module_name, separator, attribute = handler_spec.partition(":")
    if not separator or not module_name or not attribute:
        raise RuntimeError(f"invalid handler specification: {handler_spec}")

    _clear_proofloop_modules()
    original_path = list(sys.path)
    sys.path.insert(0, str(artifact))
    try:
        module = importlib.import_module(module_name)
        handler = getattr(module, attribute, None)
        if not callable(handler):
            raise RuntimeError(f"built handler is not callable: {handler_spec}")
        module_file = Path(str(module.__file__)).resolve()
        if not _inside(module_file, artifact):
            raise RuntimeError(
                "handler resolved outside build artifact: "
                f"{handler_spec} -> {module_file}"
            )
        leaked_modules: list[str] = []
        for name, loaded in sys.modules.items():
            if name != "proofloop" and not name.startswith("proofloop."):
                continue
            loaded_file = getattr(loaded, "__file__", None)
            if loaded_file is not None and not _inside(
                Path(loaded_file).resolve(), artifact
            ):
                leaked_modules.append(name)
        if leaked_modules:
            raise RuntimeError(
                "ProofLoop modules resolved outside build artifact: "
                + ", ".join(sorted(leaked_modules))
            )
    finally:
        sys.path[:] = original_path
        _clear_proofloop_modules()


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or len(arguments) % 2:
        print(
            "usage: verify_built_handlers.py ARTIFACT HANDLER[:CALLABLE] [...]",
            file=sys.stderr,
        )
        return 2
    try:
        for index in range(0, len(arguments), 2):
            verify_handler(Path(arguments[index]), arguments[index + 1])
    except (ImportError, AttributeError, RuntimeError) as error:
        print(f"Built Lambda verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified {len(arguments) // 2} built Lambda handlers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
