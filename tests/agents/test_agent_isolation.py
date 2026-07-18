from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import proofloop.agents

# Real code (not docstrings) must never import these modules...
BANNED_IMPORT_ROOTS = {
    "boto3",
    "botocore",
    "langchain",
    "langgraph",
    "crewai",
    "strands",
    "openai",
    "anthropic",
    "requests",
    "httpx",
    "socket",
    "urllib",
}
# ...nor construct/reference these domain evidence types.
FORBIDDEN_NAMES = {
    "EvidenceEnvelope",
    "Provenance",
    "WorkflowExecutionReference",
    "AssuranceEvaluation",
}

AGENTS_ROOT = Path(proofloop.agents.__file__).parent


def _agent_source_files() -> list[Path]:
    return sorted(AGENTS_ROOT.rglob("*.py"))


def _is_banned_module(module: str | None) -> bool:
    if not module:
        return False
    if module.startswith("proofloop.domain"):
        return True
    return module.split(".")[0] in BANNED_IMPORT_ROOTS


def test_agent_sources_contain_no_forbidden_imports_or_constructions() -> None:
    """AST-level check: ignores docstrings/comments, flags real code only."""

    offenders: list[str] = []
    for path in _agent_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_banned_module(alias.name):
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if _is_banned_module(node.module):
                    offenders.append(f"{path.name}: from {node.module}")
            elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                offenders.append(f"{path.name}: uses {node.id}")
    assert offenders == [], f"forbidden code references found: {offenders}"


_PROBE = """
import importlib, pkgutil, sys, json
import proofloop.agents
for m in pkgutil.walk_packages(proofloop.agents.__path__, prefix="proofloop.agents."):
    importlib.import_module(m.name)
domain = sorted(n for n in sys.modules if n.startswith("proofloop.domain"))
banned = sorted({"boto3","botocore","langchain","langgraph","crewai","strands",
                 "openai","anthropic","httpx","requests"} & set(sys.modules))
print(json.dumps({"domain": domain, "banned": banned}))
"""


def _probe_fresh_interpreter() -> dict[str, list[str]]:
    # A clean subprocess is the only reliable isolation check: within one pytest
    # process, the domain test suite has already imported proofloop.domain, so an
    # in-process sys.modules scan would be a false positive.
    src_dir = Path(proofloop.agents.__file__).parents[2]
    env = dict(os.environ, PYTHONPATH=str(src_dir))
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return json.loads(completed.stdout.strip())


def test_importing_agents_in_a_clean_interpreter_pulls_no_domain_or_sdk() -> None:
    result = _probe_fresh_interpreter()
    assert result["domain"] == [], f"domain leaked into agent import: {result['domain']}"
    assert result["banned"] == [], f"banned SDK imported: {result['banned']}"
