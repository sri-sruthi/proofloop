"""Two-direction isolation: evaluation is offline analytics, never a runtime
authority. Runtime packages must not import it; it must not import them."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import proofloop

PROOFLOOP_ROOT = Path(proofloop.__file__).parent
EVALUATION_ROOT = PROOFLOOP_ROOT / "evaluation"

# The evaluation package may import only stdlib and pydantic.
BANNED_IN_EVALUATION = {
    "boto3",
    "botocore",
    "requests",
    "httpx",
    "socket",
    "urllib",
    "pandas",
    "numpy",
    "sklearn",
}
RUNTIME_PACKAGES = (
    "proofloop.domain",
    "proofloop.agents",
    "proofloop.application",
    "proofloop.infrastructure",
    "proofloop.api",
)
# Runtime verdict/evidence types the evaluation layer must never reference.
FORBIDDEN_RUNTIME_NAMES = {
    "EvidenceEnvelope",
    "AssuranceEvaluation",
    "ComplianceReadModel",
    "ControlObservation",
}


def _imports_of(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def test_evaluation_imports_no_runtime_package_or_banned_dependency() -> None:
    offenders: list[str] = []
    for path in sorted(EVALUATION_ROOT.rglob("*.py")):
        for module in _imports_of(path):
            root = module.split(".")[0]
            if module.startswith(RUNTIME_PACKAGES) or root in BANNED_IN_EVALUATION:
                offenders.append(f"{path.name}: {module}")
    assert offenders == [], f"evaluation must stay isolated: {offenders}"


def test_evaluation_never_references_runtime_verdict_types() -> None:
    offenders: list[str] = []
    for path in sorted(EVALUATION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_RUNTIME_NAMES:
                offenders.append(f"{path.name}: {node.id}")
    assert offenders == [], f"evaluation must not touch runtime types: {offenders}"


def test_no_runtime_package_imports_the_evaluation_package() -> None:
    offenders: list[str] = []
    for path in sorted(PROOFLOOP_ROOT.rglob("*.py")):
        if EVALUATION_ROOT in path.parents or path == EVALUATION_ROOT:
            continue
        for module in _imports_of(path):
            if module.startswith("proofloop.evaluation"):
                offenders.append(f"{path.relative_to(PROOFLOOP_ROOT)}: {module}")
    assert offenders == [], (
        f"runtime code must never import evaluation: {offenders}"
    )


_PROBE = """
import importlib, pkgutil, sys, json
import proofloop.evaluation
for m in pkgutil.walk_packages(
    proofloop.evaluation.__path__, prefix="proofloop.evaluation."
):
    importlib.import_module(m.name)
runtime = sorted(
    n for n in sys.modules
    if n.startswith(("proofloop.domain", "proofloop.agents",
                     "proofloop.application", "proofloop.infrastructure",
                     "proofloop.api"))
)
banned = sorted({"boto3", "botocore", "pandas", "numpy", "sklearn",
                 "requests", "httpx"} & set(sys.modules))
print(json.dumps({"runtime": runtime, "banned": banned}))
"""


def test_importing_evaluation_in_a_clean_interpreter_pulls_no_runtime() -> None:
    src_dir = PROOFLOOP_ROOT.parent
    env = dict(os.environ, PYTHONPATH=str(src_dir))
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    result = json.loads(completed.stdout.strip())
    assert result["runtime"] == [], f"runtime leaked: {result['runtime']}"
    assert result["banned"] == [], f"banned dependency: {result['banned']}"


def test_evaluation_output_speaks_no_runtime_verdict_vocabulary() -> None:
    """The report writer must never emit GREEN/AMBER/RED verdict fields, so its
    output cannot even be mistaken for (or spliced into) a compliance verdict."""

    report_source = (EVALUATION_ROOT / "report.py").read_text(encoding="utf-8")
    for verdict in ('"GREEN"', '"AMBER"', '"RED"', "overall_compliance_status"):
        assert verdict not in report_source, (
            f"evaluation output must not carry runtime verdict field {verdict}"
        )
