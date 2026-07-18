from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.smoke_bedrock_invoice import _is_successful_smoke


def test_real_bedrock_smoke_refuses_to_run_without_explicit_guard() -> None:
    repository = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment.pop("PROOFLOOP_ALLOW_REAL_MODEL_SMOKE", None)

    completed = subprocess.run(
        [sys.executable, "scripts/smoke_bedrock_invoice.py"],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "Real Bedrock smoke is disabled" in completed.stderr
    assert "invoice" not in completed.stdout.lower()


def test_real_bedrock_smoke_requires_workflow_and_compliance_success() -> None:
    failed = {
        "workflow_status": "EXTRACTION_FAILED",
        "model_usage": {"model_calls": 1},
        "evidence": [{"evidence_id": "safe-opaque-id"}],
        "compliance": {"overall_compliance_status": "RED"},
    }
    succeeded = {
        "workflow_status": "COMPLETED",
        "model_usage": {"model_calls": 1},
        "evidence": [{"evidence_id": "safe-opaque-id"}],
        "compliance": {"overall_compliance_status": "GREEN"},
    }

    assert _is_successful_smoke(200, failed) is False
    assert _is_successful_smoke(500, succeeded) is False
    assert _is_successful_smoke(200, succeeded) is True
