from __future__ import annotations

import ast
from pathlib import Path

import proofloop.application


def test_application_contracts_and_services_do_not_import_infrastructure() -> None:
    root = Path(proofloop.application.__file__).parent
    offenders = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("proofloop.infrastructure")
            ):
                offenders.append(f"{path.name}: from {node.module}")
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.name}: import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith("proofloop.infrastructure")
                )
    assert offenders == []
