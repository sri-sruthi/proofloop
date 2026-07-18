"""CLI tests: validate-first, safe failure, deterministic offline outputs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "evaluate_extraction.py"


def _dataset_payload() -> dict:  # type: ignore[type-arg]
    record = {
        "schema_version": "1.0.0",
        "dataset_record_id": "r1",
        "dataset_provenance": "SYNTHETIC",
        "split": "DEVELOPMENT",
        "expected_fields": {"invoice_number": "INV-1", "total": "10.00"},
        "predicted_fields": {"invoice_number": "INV-1", "total": "10.00"},
        "model_reported_confidence": 0.9,
        "provider_config_id": "stub-provider-v1",
        "prompt_config_id": "invoice-extraction-v1",
        "latency_ms": 100,
        "input_tokens": 500,
        "output_tokens": 100,
    }
    return {"schema_version": "1.0.0", "records": [record]}


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "src"))
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_valid_input_writes_deterministic_json_and_markdown(
    tmp_path: Path,
) -> None:
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text(json.dumps(_dataset_payload()), encoding="utf-8")
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"

    first = _run_cli(
        str(dataset_file),
        "--json-out",
        str(json_out),
        "--markdown-out",
        str(md_out),
        cwd=tmp_path,
    )
    assert first.returncode == 0, first.stderr
    first_json = json_out.read_text(encoding="utf-8")
    first_md = md_out.read_text(encoding="utf-8")
    assert json.loads(first_json)["status"] in {"OK", "INSUFFICIENT_EVIDENCE"}
    assert "ProofLoop" in first_md

    second = _run_cli(
        str(dataset_file),
        "--json-out",
        str(json_out),
        "--markdown-out",
        str(md_out),
        cwd=tmp_path,
    )
    assert second.returncode == 0
    assert json_out.read_text(encoding="utf-8") == first_json
    assert md_out.read_text(encoding="utf-8") == first_md


def test_invalid_probability_fails_safely_before_any_output(
    tmp_path: Path,
) -> None:
    payload = _dataset_payload()
    payload["records"][0]["model_reported_confidence"] = 1.7
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text(json.dumps(payload), encoding="utf-8")
    json_out = tmp_path / "report.json"

    result = _run_cli(
        str(dataset_file), "--json-out", str(json_out), cwd=tmp_path
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not json_out.exists()


def test_malformed_json_fails_safely(tmp_path: Path) -> None:
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text("{not json", encoding="utf-8")
    result = _run_cli(str(dataset_file), cwd=tmp_path)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_missing_file_fails_safely(tmp_path: Path) -> None:
    result = _run_cli(str(tmp_path / "absent.json"), cwd=tmp_path)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_optional_pricing_flags_produce_cost_estimates(tmp_path: Path) -> None:
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text(json.dumps(_dataset_payload()), encoding="utf-8")
    json_out = tmp_path / "report.json"

    result = _run_cli(
        str(dataset_file),
        "--json-out",
        str(json_out),
        "--input-token-price-per-1k",
        "3.00",
        "--output-token-price-per-1k",
        "15.00",
        "--price-currency",
        "USD",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["estimated_cost"]["currency"] == "USD"


def test_cli_source_never_touches_aws_or_runtime_state() -> None:
    source = CLI.read_text(encoding="utf-8")
    for banned in ("boto3", "botocore", "bedrock", "proofloop.domain",
                   "proofloop.agents", "proofloop.application",
                   "proofloop.infrastructure", "proofloop.api"):
        assert banned not in source, f"CLI must never reference {banned}"
