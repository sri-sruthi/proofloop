from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_demo_script_prints_customer_readable_sequence_without_sensitive_payloads() -> None:
    repository = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/demo_proofloop.py"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "GREEN -> AMBER -> RED -> AMBER -> GREEN" in completed.stdout
    assert "Fresh post-remediation proof" in completed.stdout
    assert "Timeline (last seven days)" in completed.stdout
    assert "Supporting evidence:" in completed.stdout
    assert "canary-48h-safe-canary-failure" in completed.stdout
    assert "Customer impact:" in completed.stdout
    assert "Remediation:" in completed.stdout
    assert "raw_invoice" not in completed.stdout
    assert "customer_name" not in completed.stdout
