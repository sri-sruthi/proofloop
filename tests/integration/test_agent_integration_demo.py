from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_agent_to_compliance_demo_covers_required_safe_scenes() -> None:
    repository = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/demo_agent_to_compliance.py"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )

    output = completed.stdout
    for expected in (
        "Poisoned invoice: redacted-before-model=yes; injection-channel=untrusted",
        "Duplicate/HITL: disposition=BLOCK; human-review-called=yes",
        "Agent evidence to compliance: GREEN",
        "Idempotent replay: 4 DUPLICATE receipts",
        "Conflict quarantine: AMBER",
        "Malformed model output: EXTRACTION_FAILED -> RED",
        "Tool failure: RECONCILIATION_FAILED -> AMBER",
        "Safe canary failure: RED",
        "Repair declaration only: AMBER",
        "Fresh post-repair runtime + canary: GREEN",
        "Status path: GREEN -> AMBER -> GREEN -> RED -> AMBER -> GREEN",
        "Timeline entries:",
        "Incidents:",
        "Bounded usage: calls=1 input_tokens=120 output_tokens=40",
        "No payment tool: confirmed",
    ):
        assert expected in output
    for forbidden in (
        "billing@acme.example.com",
        "123456789012",
        "415 555 2671",
        "IGNORE ALL PREVIOUS INSTRUCTIONS",
    ):
        assert forbidden not in output

