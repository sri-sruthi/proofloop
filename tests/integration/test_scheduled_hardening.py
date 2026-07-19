from __future__ import annotations

import logging
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from infra.scripts.copy_runtime_package import copy_runtime_package
from proofloop.infrastructure import scheduled_handler


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class _SyncResult:
    class Compliance:
        overall_compliance_status = type("Status", (), {"value": "GREEN"})()

    compliance = Compliance()


class _PartiallyFailingService:
    def __init__(self) -> None:
        self.attempted: list[str] = []

    def list_agent_scopes(self) -> tuple[str, ...]:
        return ("scope-a", "scope-b", "scope-c")

    def sync(self, scope: str) -> _SyncResult:
        self.attempted.append(scope)
        if scope == "scope-b":
            raise RuntimeError("api_key=do-not-log evidence=private-payload")
        return _SyncResult()


def test_scheduled_handler_attempts_every_scope_then_raises_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _PartiallyFailingService()
    monkeypatch.setattr(scheduled_handler, "_service", service)
    canary_scopes: list[str] = []
    monkeypatch.setattr(scheduled_handler, "_canary_emitter", canary_scopes.append)
    event = {
        "source": "proofloop.reconciliation",
        "api_key": "event-secret",
        "payload": "event-private-payload",
    }

    with caplog.at_level(logging.INFO), pytest.raises(
        RuntimeError,
        match=r"scheduled reconciliation failed for 1 of 3 agent scopes",
    ):
        scheduled_handler.scheduled_handler(event, None)

    assert service.attempted == ["scope-a", "scope-b", "scope-c"]
    assert canary_scopes == ["scope-a", "scope-b", "scope-c"]
    assert "do-not-log" not in caplog.text
    assert "private-payload" not in caplog.text
    assert "event-secret" not in caplog.text
    assert "event-private-payload" not in caplog.text


def test_schedule_has_bounded_retry_and_explicit_sqs_dlq() -> None:
    template = (REPOSITORY_ROOT / "infra" / "template.yaml").read_text(
        encoding="utf-8"
    )
    rule = template.split(
        "  ProofLoopScheduledFunctionFiveMinuteReconciliation:", 1
    )[1].split("\n  ProofLoopScheduledFunctionFiveMinuteReconciliationPermission:", 1)[0]

    assert "MaximumEventAgeInSeconds: 300" in rule
    assert "MaximumRetryAttempts: 2" in rule
    assert "DeadLetterConfig:" in rule
    assert "Arn: !GetAtt ProofLoopScheduledDeadLetterQueue.Arn" in rule
    assert "State: !If [ReconciliationScheduleEnabled, ENABLED, DISABLED]" in rule
    assert "sqs:*" not in template
    assert "Resource: \"*\"" not in template


def test_lambda_async_failures_have_bounded_retries_and_failure_destination() -> None:
    template = (REPOSITORY_ROOT / "infra" / "template.yaml").read_text(
        encoding="utf-8"
    )
    scheduled = template.split("  ProofLoopScheduledFunction:", 1)[1].split(
        "  ProofLoopScheduledFunctionFiveMinuteReconciliation:", 1
    )[0]

    assert "EventInvokeConfig:" in scheduled
    rule = template.split(
        "  ProofLoopScheduledFunctionFiveMinuteReconciliation:", 1
    )[1].split("\n  ProofLoopScheduledFunctionFiveMinuteReconciliationPermission:", 1)[0]

    assert scheduled.count("MaximumEventAgeInSeconds: 300") == 1
    assert scheduled.count("MaximumRetryAttempts: 2") == 1
    assert rule.count("MaximumEventAgeInSeconds: 300") == 1
    assert rule.count("MaximumRetryAttempts: 2") == 1
    assert "DestinationConfig:" in scheduled
    assert "OnFailure:" in scheduled
    assert scheduled.count("Type: SQS") == 1
    assert "AWS::SQS::QueuePolicy" in template


def test_both_lambda_roles_can_commit_dynamodb_transactions() -> None:
    template = (REPOSITORY_ROOT / "infra" / "template.yaml").read_text(
        encoding="utf-8"
    )
    api = template.split("  ProofLoopApiFunction:", 1)[1].split(
        "\n  ProofLoopScheduledFunction:", 1
    )[0]
    scheduled = template.split("  ProofLoopScheduledFunction:", 1)[1].split(
        "\nOutputs:", 1
    )[0]

    assert api.count("- dynamodb:TransactWriteItems") == 1
    assert scheduled.count("- dynamodb:TransactWriteItems") == 1


def test_agent_registry_gsi_replaces_scheduled_table_scan() -> None:
    template = (REPOSITORY_ROOT / "infra" / "template.yaml").read_text(
        encoding="utf-8"
    )
    table = template.split("  ProofLoopEvidenceTable:", 1)[1].split(
        "\n  ProofLoopApiLogGroup:", 1
    )[0]
    scheduled = template.split("  ProofLoopScheduledFunction:", 1)[1].split(
        "\nOutputs:", 1
    )[0]

    assert "- AttributeName: GSI1PK" in table
    assert "- AttributeName: GSI1SK" in table
    assert "GlobalSecondaryIndexes:" in table
    assert "IndexName: AgentRegistryIndex" in table
    assert "AttributeName: GSI1PK\n              KeyType: HASH" in table
    assert "AttributeName: GSI1SK\n              KeyType: RANGE" in table
    assert "ProjectionType: ALL" in table
    assert "dynamodb:Scan" not in scheduled
    assert (
        'Resource: !Sub "${ProofLoopEvidenceTable.Arn}/index/AgentRegistryIndex"'
        in scheduled
    )


def test_credential_free_validator_rejects_structurally_wrong_retry_budget(
    tmp_path: Path,
) -> None:
    template = (REPOSITORY_ROOT / "infra" / "template.yaml").read_text(
        encoding="utf-8"
    )
    assert "MaximumRetryAttempts: 2" in template
    bad_template = template.replace(
        "MaximumRetryAttempts: 2",
        "MaximumRetryAttempts: 185",
        1,
    )
    # A decoy preserves the old snippet, so a global substring check would pass.
    bad_template += "\n# MaximumRetryAttempts: 2\n"
    template_path = tmp_path / "template.yaml"
    template_path.write_text(bad_template, encoding="utf-8")
    makefile_path = tmp_path / "Makefile"
    shutil.copy(REPOSITORY_ROOT / "infra" / "lambda" / "Makefile", makefile_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "infra" / "scripts" / "validate_template.py"),
            "--template",
            str(template_path),
            "--makefile",
            str(makefile_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "MaximumRetryAttempts" in completed.stderr


def test_ci_builds_on_target_architecture_and_verifies_built_handlers() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "AWS_DEFAULT_REGION: ap-south-1" in workflow
    assert "AWS_REGION: ap-south-1" in workflow
    assert 'SAM_CLI_TELEMETRY: "0"' in workflow
    assert "runner: ubuntu-latest" in workflow
    assert "runner: ubuntu-24.04-arm" in workflow
    assert "runs-on: ${{ matrix.runner }}" in workflow
    assert "use-installer: true" in workflow
    assert "sam validate --lint --template-file infra/template.yaml" in workflow
    assert "Verify target architecture" in workflow
    assert "sam build -t infra/template.yaml" in workflow
    assert "--use-container" not in workflow
    assert "python infra/scripts/verify_built_handlers.py" in workflow
    assert ".aws-sam/build/ProofLoopApiFunction" in workflow
    assert ".aws-sam/build/ProofLoopScheduledFunction" in workflow


def test_built_handler_verifier_loads_each_handler_from_its_artifact(
    tmp_path: Path,
) -> None:
    artifact_paths: list[Path] = []
    for logical_id in ("ProofLoopApiFunction", "ProofLoopScheduledFunction"):
        artifact = tmp_path / logical_id
        copy_runtime_package(
            REPOSITORY_ROOT / "src" / "proofloop", artifact / "proofloop"
        )
        artifact_paths.append(artifact)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "infra" / "scripts" / "verify_built_handlers.py"),
            str(artifact_paths[0]),
            "proofloop.infrastructure.lambda_handler:handler",
            str(artifact_paths[1]),
            "proofloop.infrastructure.scheduled_handler:scheduled_handler",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Verified 2 built Lambda handlers." in completed.stdout
