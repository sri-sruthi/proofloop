from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (REPOSITORY_ROOT / "infra" / "template.yaml").read_text(
    encoding="utf-8"
)


def _block(name: str) -> str:
    lines = TEMPLATE.splitlines()
    prefix = f"  {name}:"
    starts = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    assert len(starts) == 1, f"expected one {name} block, found {len(starts)}"
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.startswith("  ") and not line.startswith("    "):
            end = index
            break
    return "\n".join(lines[start:end])


def _parameter_pattern(name: str) -> str:
    parameter = _block(name)
    pattern_lines = [
        line.strip() for line in parameter.splitlines() if "AllowedPattern:" in line
    ]
    assert len(pattern_lines) == 1
    return pattern_lines[0].split("AllowedPattern:", 1)[1].strip().strip("'\"")


def _run_validator(
    tmp_path: Path,
    template: str,
) -> subprocess.CompletedProcess[str]:
    template_path = tmp_path / "template.yaml"
    template_path.write_text(template, encoding="utf-8")
    makefile_path = tmp_path / "Makefile"
    shutil.copy(REPOSITORY_ROOT / "infra" / "lambda" / "Makefile", makefile_path)
    return subprocess.run(
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


def test_allowed_origin_is_required_non_wildcard_and_injected() -> None:
    parameter = _block("AllowedOrigin")

    assert "    Type: String" in parameter
    assert "    Default:" not in parameter
    pattern = _parameter_pattern("AllowedOrigin")
    assert re.fullmatch(pattern, "http://localhost:8000")
    assert not re.fullmatch(pattern, "*")
    assert "PROOFLOOP_ALLOWED_ORIGIN: !Ref AllowedOrigin" in _block(
        "ProofLoopApiFunction"
    )


def test_reconciliation_schedule_is_explicit_and_disabled_by_default() -> None:
    parameter = _block("EnableReconciliationSchedule")

    assert '    Default: "false"' in parameter
    assert '      - "true"' in parameter
    assert '      - "false"' in parameter
    condition = _block("ReconciliationScheduleEnabled")
    assert "!Equals" in condition
    assert "!Ref EnableReconciliationSchedule" in condition
    assert '    - "true"' in condition
    assert (
        "Enabled: !If [ReconciliationScheduleEnabled, true, false]"
        in _block("ProofLoopScheduledFunction")
    )


def test_table_lifecycle_is_explicit_for_controlled_development() -> None:
    table = _block("ProofLoopEvidenceTable")

    assert "    DeletionPolicy: Delete" in table
    assert "    UpdateReplacePolicy: Retain" in table


def test_alarm_email_is_required_and_stack_managed() -> None:
    email = _block("AlarmNotificationEmail")

    assert "    Type: String" in email
    assert "    NoEcho: true" in email
    assert "    Default:" not in email
    pattern = _parameter_pattern("AlarmNotificationEmail")
    assert re.fullmatch(pattern, "owner@example.invalid")
    assert not re.fullmatch(pattern, "not-an-email")
    assert "AWS::SNS::Topic" in _block("ProofLoopAlarmTopic")
    subscription = _block("ProofLoopAlarmEmailSubscription")
    assert "AWS::SNS::Subscription" in subscription
    assert "Protocol: email" in subscription
    assert "Endpoint: !Ref AlarmNotificationEmail" in subscription
    assert "TopicArn: !Ref ProofLoopAlarmTopic" in subscription


def test_ten_development_alarms_use_approved_metrics_and_dimensions() -> None:
    alarm_cases = {
        "ProofLoopApiErrorsAlarm": (
            "AWS/Lambda",
            "Errors",
            "Sum",
            ("Name: FunctionName", "Value: !Ref ProofLoopApiFunction"),
        ),
        "ProofLoopApiThrottlesAlarm": (
            "AWS/Lambda",
            "Throttles",
            "Sum",
            ("Name: FunctionName", "Value: !Ref ProofLoopApiFunction"),
        ),
        "ProofLoopScheduledErrorsAlarm": (
            "AWS/Lambda",
            "Errors",
            "Sum",
            ("Name: FunctionName", "Value: !Ref ProofLoopScheduledFunction"),
        ),
        "ProofLoopScheduledThrottlesAlarm": (
            "AWS/Lambda",
            "Throttles",
            "Sum",
            ("Name: FunctionName", "Value: !Ref ProofLoopScheduledFunction"),
        ),
        "ProofLoopEventBridgeDeliveryDlqDepthAlarm": (
            "AWS/SQS",
            "ApproximateNumberOfMessagesVisible",
            "Maximum",
            (
                "Name: QueueName",
                "Value: !GetAtt ProofLoopScheduledDeadLetterQueue.QueueName",
            ),
        ),
        "ProofLoopLambdaFailureDlqDepthAlarm": (
            "AWS/SQS",
            "ApproximateNumberOfMessagesVisible",
            "Maximum",
            (
                "Name: QueueName",
                "Value: !GetAtt ProofLoopScheduledFunctionEventInvokeConfigOnFailureQueue.QueueName",
            ),
        ),
        "ProofLoopEventBridgeFailedInvocationsAlarm": (
            "AWS/Events",
            "FailedInvocations",
            "Sum",
            (
                "Name: RuleName",
                "Value: !Ref ProofLoopScheduledFunctionFiveMinuteReconciliation",
            ),
        ),
        "ProofLoopHttpApi5xxAlarm": (
            "AWS/ApiGateway",
            "5xx",
            "Sum",
            (
                "Name: ApiId",
                "Value: !Ref ProofLoopHttpApi",
                "Name: Stage",
                'Value: "$default"',
            ),
        ),
        "ProofLoopDynamoDbReadThrottlesAlarm": (
            "AWS/DynamoDB",
            "ReadThrottleEvents",
            "Sum",
            ("Name: TableName", "Value: !Ref ProofLoopEvidenceTable"),
        ),
        "ProofLoopDynamoDbWriteThrottlesAlarm": (
            "AWS/DynamoDB",
            "WriteThrottleEvents",
            "Sum",
            ("Name: TableName", "Value: !Ref ProofLoopEvidenceTable"),
        ),
    }

    assert TEMPLATE.count("    Type: AWS::CloudWatch::Alarm") == 10
    for logical_id, (namespace, metric, statistic, dimensions) in alarm_cases.items():
        alarm = _block(logical_id)
        assert "Type: AWS::CloudWatch::Alarm" in alarm
        assert f"Namespace: {namespace}" in alarm
        assert f"MetricName: {metric}" in alarm
        assert f"Statistic: {statistic}" in alarm
        assert "Period: 300" in alarm
        assert "EvaluationPeriods: 1" in alarm
        assert "Threshold: 1" in alarm
        assert "ComparisonOperator: GreaterThanOrEqualToThreshold" in alarm
        assert "TreatMissingData: notBreaching" in alarm
        assert "ActionsEnabled: true" in alarm
        assert "- !Ref ProofLoopAlarmTopic" in alarm
        assert all(dimension in alarm for dimension in dimensions)


def test_credential_free_validator_accepts_hardened_template(tmp_path: Path) -> None:
    completed = _run_validator(tmp_path, TEMPLATE)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "SAM package guardrails passed."


@pytest.mark.parametrize(
    ("original", "replacement", "expected_issue"),
    (
        (
            "PROOFLOOP_ALLOWED_ORIGIN: !Ref AllowedOrigin",
            'PROOFLOOP_ALLOWED_ORIGIN: "*"',
            "PROOFLOOP_ALLOWED_ORIGIN",
        ),
        (
            'Default: "false"',
            'Default: "true"',
            "EnableReconciliationSchedule.Default",
        ),
        (
            "UpdateReplacePolicy: Retain",
            "UpdateReplacePolicy: Delete",
            "UpdateReplacePolicy",
        ),
        (
            "MetricName: Errors",
            "MetricName: Invocations",
            "ProofLoopApiErrorsAlarm.MetricName",
        ),
        (
            "        - !Ref ProofLoopAlarmTopic",
            "        - !Ref ProofLoopApiFunction",
            "ProofLoopApiErrorsAlarm.AlarmActions",
        ),
    ),
)
def test_credential_free_validator_rejects_operational_guardrail_drift(
    tmp_path: Path,
    original: str,
    replacement: str,
    expected_issue: str,
) -> None:
    assert original in TEMPLATE
    bad_template = TEMPLATE.replace(original, replacement, 1)

    completed = _run_validator(tmp_path, bad_template)

    assert completed.returncode == 1
    assert expected_issue in completed.stderr


def test_assurance_boundary_is_required_parameterized_and_not_hard_coded() -> None:
    parameter = _block("AssuranceBoundaryId")

    assert "    Type: String" in parameter
    assert "    Default:" not in parameter
    pattern = _parameter_pattern("AssuranceBoundaryId")
    assert re.fullmatch(pattern, "proofloop-demo-dev-invoices")
    assert not re.fullmatch(pattern, "*")
    assert not re.fullmatch(pattern, "")

    for function in ("ProofLoopApiFunction", "ProofLoopScheduledFunction"):
        assert (
            "PROOFLOOP_DEMO_BOUNDARY_ID: !Ref AssuranceBoundaryId"
            in _block(function)
        ), f"{function} must inject the AssuranceBoundaryId parameter"

    # The previously hard-coded wrong boundary must be absent everywhere so a
    # deployment can never silently certify a different customer boundary.
    assert "proofloop-demo-development-invoices" not in TEMPLATE


def test_deployment_readme_passes_the_approved_assurance_boundary() -> None:
    readme = (REPOSITORY_ROOT / "infra" / "README.md").read_text(encoding="utf-8")
    assert "AssuranceBoundaryId=proofloop-demo-dev-invoices" in readme


@pytest.mark.parametrize(
    ("original", "replacement", "expected_issue"),
    (
        (
            "PROOFLOOP_DEMO_BOUNDARY_ID: !Ref AssuranceBoundaryId",
            "PROOFLOOP_DEMO_BOUNDARY_ID: proofloop-demo-development-invoices",
            "PROOFLOOP_DEMO_BOUNDARY_ID",
        ),
        (
            "PROOFLOOP_DEMO_BOUNDARY_ID: !Ref AssuranceBoundaryId",
            'PROOFLOOP_DEMO_BOUNDARY_ID: ""',
            "PROOFLOOP_DEMO_BOUNDARY_ID",
        ),
    ),
)
def test_credential_free_validator_rejects_assurance_boundary_drift(
    tmp_path: Path,
    original: str,
    replacement: str,
    expected_issue: str,
) -> None:
    assert original in TEMPLATE
    bad_template = TEMPLATE.replace(original, replacement, 1)

    completed = _run_validator(tmp_path, bad_template)

    assert completed.returncode == 1
    assert expected_issue in completed.stderr
