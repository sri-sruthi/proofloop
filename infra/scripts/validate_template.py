#!/usr/bin/env python3
"""Credential-free structural guardrails for the ProofLoop SAM package.

This deliberately validates only the small, known ProofLoop template shape.  It
does not pretend to be a YAML or CloudFormation parser; ``sam validate`` remains
the authoritative syntax/schema check in CI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


FORBIDDEN_RESOURCE_TYPES = {
    "AWS::Cognito::IdentityPool",
    "AWS::Cognito::UserPool",
    "AWS::EC2::NatGateway",
    "AWS::ECS::Cluster",
    "AWS::EKS::Cluster",
    "AWS::OpenSearchService::Domain",
    "AWS::RDS::DBCluster",
    "AWS::RDS::DBInstance",
    "AWS::Redshift::Cluster",
}
FUNCTIONS = {
    "ProofLoopApiFunction": "proofloop.infrastructure.lambda_handler.handler",
    "ProofLoopScheduledFunction": (
        "proofloop.infrastructure.scheduled_handler.scheduled_handler"
    ),
}
LOG_GROUPS = (
    "ProofLoopApiLogGroup",
    "ProofLoopScheduledLogGroup",
    "ProofLoopHttpApiAccessLogGroup",
)
ALARM_SPECS: dict[
    str,
    tuple[str, str, str, tuple[tuple[str, str], ...]],
] = {
    "ProofLoopApiErrorsAlarm": (
        "AWS/Lambda",
        "Errors",
        "Sum",
        (("FunctionName", "!Ref ProofLoopApiFunction"),),
    ),
    "ProofLoopApiThrottlesAlarm": (
        "AWS/Lambda",
        "Throttles",
        "Sum",
        (("FunctionName", "!Ref ProofLoopApiFunction"),),
    ),
    "ProofLoopScheduledErrorsAlarm": (
        "AWS/Lambda",
        "Errors",
        "Sum",
        (("FunctionName", "!Ref ProofLoopScheduledFunction"),),
    ),
    "ProofLoopScheduledThrottlesAlarm": (
        "AWS/Lambda",
        "Throttles",
        "Sum",
        (("FunctionName", "!Ref ProofLoopScheduledFunction"),),
    ),
    "ProofLoopEventBridgeDeliveryDlqDepthAlarm": (
        "AWS/SQS",
        "ApproximateNumberOfMessagesVisible",
        "Maximum",
        (("QueueName", "!GetAtt ProofLoopScheduledDeadLetterQueue.QueueName"),),
    ),
    "ProofLoopLambdaFailureDlqDepthAlarm": (
        "AWS/SQS",
        "ApproximateNumberOfMessagesVisible",
        "Maximum",
        (
            (
                "QueueName",
                "!GetAtt ProofLoopScheduledFunctionEventInvokeConfigOnFailureQueue.QueueName",
            ),
        ),
    ),
    "ProofLoopEventBridgeFailedInvocationsAlarm": (
        "AWS/Events",
        "FailedInvocations",
        "Sum",
        (
            (
                "RuleName",
                "!Ref ProofLoopScheduledFunctionFiveMinuteReconciliation",
            ),
        ),
    ),
    "ProofLoopHttpApi5xxAlarm": (
        "AWS/ApiGateway",
        "5xx",
        "Sum",
        (("ApiId", "!Ref ProofLoopHttpApi"), ("Stage", '"$default"')),
    ),
    "ProofLoopDynamoDbReadThrottlesAlarm": (
        "AWS/DynamoDB",
        "ReadThrottleEvents",
        "Sum",
        (("TableName", "!Ref ProofLoopEvidenceTable"),),
    ),
    "ProofLoopDynamoDbWriteThrottlesAlarm": (
        "AWS/DynamoDB",
        "WriteThrottleEvents",
        "Sum",
        (("TableName", "!Ref ProofLoopEvidenceTable"),),
    ),
}


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _find_block(
    lines: Sequence[str],
    key: str,
    indent: int,
    issues: list[str],
) -> list[str]:
    marker = f"{' ' * indent}{key}:"
    starts = [index for index, line in enumerate(lines) if line.rstrip() == marker]
    if len(starts) != 1:
        issues.append(f"expected exactly one {key} block at indentation {indent}")
        return []
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if (
            line.strip()
            and not line.lstrip().startswith("#")
            and _indent(line) <= indent
        ):
            end = index
            break
    return list(lines[start:end])


def _expect_value(
    lines: Sequence[str],
    key: str,
    indent: int,
    expected: str,
    issues: list[str],
    owner: str,
) -> None:
    wanted = f"{' ' * indent}{key}: {expected}"
    matches = [line for line in lines if line.rstrip() == wanted]
    if len(matches) != 1:
        issues.append(f"{owner}.{key} must be {expected}")


def _direct_values(lines: Sequence[str], key: str, indent: int) -> list[str]:
    prefix = f"{' ' * indent}{key}:"
    values: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            values.append(line[len(prefix) :].strip())
    return values


def _expect_sequence(
    lines: Sequence[str],
    expected: Sequence[str],
    issues: list[str],
    description: str,
) -> None:
    width = len(expected)
    found = any(
        list(lines[index : index + width]) == list(expected)
        for index in range(len(lines))
    )
    if not found:
        issues.append(description)


def _validate_parameters(lines: Sequence[str], issues: list[str]) -> None:
    api_key = _find_block(lines, "ApiKey", 2, issues)
    _expect_value(api_key, "Type", 4, "String", issues, "ApiKey")
    _expect_value(api_key, "NoEcho", 4, "true", issues, "ApiKey")
    if _direct_values(api_key, "Default", 4):
        issues.append("ApiKey must not define a default")
    allowed_origin = _find_block(lines, "AllowedOrigin", 2, issues)
    _expect_value(allowed_origin, "Type", 4, "String", issues, "AllowedOrigin")
    _expect_value(
        allowed_origin,
        "AllowedPattern",
        4,
        "'^https?://[^*\\s]+$'",
        issues,
        "AllowedOrigin",
    )
    if _direct_values(allowed_origin, "Default", 4):
        issues.append("AllowedOrigin must not define a default")
    assurance_boundary = _find_block(lines, "AssuranceBoundaryId", 2, issues)
    _expect_value(
        assurance_boundary, "Type", 4, "String", issues, "AssuranceBoundaryId"
    )
    _expect_value(
        assurance_boundary,
        "AllowedPattern",
        4,
        "'^[a-z0-9]+(-[a-z0-9]+)*$'",
        issues,
        "AssuranceBoundaryId",
    )
    if _direct_values(assurance_boundary, "Default", 4):
        issues.append("AssuranceBoundaryId must not define a default")
    schedule_enabled = _find_block(
        lines, "EnableReconciliationSchedule", 2, issues
    )
    _expect_value(
        schedule_enabled,
        "Type",
        4,
        "String",
        issues,
        "EnableReconciliationSchedule",
    )
    _expect_value(
        schedule_enabled,
        "Default",
        4,
        '"false"',
        issues,
        "EnableReconciliationSchedule",
    )
    _expect_sequence(
        schedule_enabled,
        (
            "    AllowedValues:",
            '      - "true"',
            '      - "false"',
        ),
        issues,
        "EnableReconciliationSchedule must allow only true and false",
    )
    alarm_email = _find_block(lines, "AlarmNotificationEmail", 2, issues)
    _expect_value(
        alarm_email,
        "Type",
        4,
        "String",
        issues,
        "AlarmNotificationEmail",
    )
    _expect_value(
        alarm_email,
        "NoEcho",
        4,
        "true",
        issues,
        "AlarmNotificationEmail",
    )
    _expect_value(
        alarm_email,
        "AllowedPattern",
        4,
        "'^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'",
        issues,
        "AlarmNotificationEmail",
    )
    if _direct_values(alarm_email, "Default", 4):
        issues.append("AlarmNotificationEmail must not define a default")
    for name in ("BedrockModelId", "BedrockModelArn", "BedrockRegion"):
        parameter = _find_block(lines, name, 2, issues)
        _expect_value(parameter, "Type", 4, "String", issues, name)
        if _direct_values(parameter, "Default", 4):
            issues.append(f"{name} must not define a hard-coded default")
    for name in (
        "MaxModelCalls",
        "MaxModelRetries",
        "MaxOutputTokens",
        "ModelTimeoutSeconds",
    ):
        parameter = _find_block(lines, name, 2, issues)
        _expect_value(parameter, "Type", 4, "Number", issues, name)


def _validate_table(lines: Sequence[str], issues: list[str]) -> None:
    table = _find_block(lines, "ProofLoopEvidenceTable", 2, issues)
    _expect_value(
        table,
        "Type",
        4,
        "AWS::DynamoDB::Table",
        issues,
        "ProofLoopEvidenceTable",
    )
    _expect_value(
        table,
        "DeletionPolicy",
        4,
        "Delete",
        issues,
        "ProofLoopEvidenceTable",
    )
    _expect_value(
        table,
        "UpdateReplacePolicy",
        4,
        "Retain",
        issues,
        "ProofLoopEvidenceTable",
    )
    _expect_value(
        table,
        "BillingMode",
        6,
        "PAY_PER_REQUEST",
        issues,
        "ProofLoopEvidenceTable",
    )
    _expect_value(table, "SSEEnabled", 8, "true", issues, "ProofLoopEvidenceTable")
    if "        AttributeName: ttl" not in table:
        issues.append("ProofLoopEvidenceTable TTL attribute must be ttl")
    _expect_value(table, "Enabled", 8, "true", issues, "ProofLoopEvidenceTable TTL")
    _expect_sequence(
        table,
        ("        - AttributeName: GSI1PK", "          AttributeType: S"),
        issues,
        "ProofLoopEvidenceTable must define string attribute GSI1PK",
    )
    _expect_sequence(
        table,
        ("        - AttributeName: GSI1SK", "          AttributeType: S"),
        issues,
        "ProofLoopEvidenceTable must define string attribute GSI1SK",
    )
    _expect_sequence(
        table,
        (
            "        - IndexName: AgentRegistryIndex",
            "          KeySchema:",
            "            - AttributeName: GSI1PK",
            "              KeyType: HASH",
            "            - AttributeName: GSI1SK",
            "              KeyType: RANGE",
            "          Projection:",
            "            ProjectionType: ALL",
        ),
        issues,
        "ProofLoopEvidenceTable must define the AgentRegistryIndex GSI",
    )


def _validate_functions(lines: Sequence[str], issues: list[str]) -> None:
    for logical_id, handler in FUNCTIONS.items():
        function = _find_block(lines, logical_id, 2, issues)
        _expect_value(
            function,
            "Type",
            4,
            "AWS::Serverless::Function",
            issues,
            logical_id,
        )
        _expect_value(function, "BuildMethod", 6, "makefile", issues, logical_id)
        _expect_value(function, "CodeUri", 6, "../", issues, logical_id)
        _expect_value(function, "Handler", 6, handler, issues, logical_id)
        _expect_value(function, "Runtime", 6, "python3.13", issues, logical_id)
        _expect_value(function, "LogFormat", 8, "JSON", issues, logical_id)
        _expect_value(
            function,
            "PROOFLOOP_DEMO_BOUNDARY_ID",
            10,
            "!Ref AssuranceBoundaryId",
            issues,
            logical_id,
        )
        if function.count("                - dynamodb:TransactWriteItems") != 1:
            issues.append(f"{logical_id} requires dynamodb:TransactWriteItems")
        resources = _direct_values(function, "Resource", 14)
        if any(value in {'"*"', "'*'", "*"} for value in resources):
            issues.append(f"{logical_id} IAM Resource must not be wildcard")
        if any("*" in line for line in function if line.strip().startswith("- ")):
            issues.append(f"{logical_id} IAM actions must not use wildcards")

    api_function = _find_block(lines, "ProofLoopApiFunction", 2, issues=[])
    _expect_value(
        api_function,
        "PROOFLOOP_ALLOWED_ORIGIN",
        10,
        "!Ref AllowedOrigin",
        issues,
        "ProofLoopApiFunction",
    )
    if "                - dynamodb:Scan" in api_function:
        issues.append("ProofLoopApiFunction must not have dynamodb:Scan")
    scheduled = _find_block(lines, "ProofLoopScheduledFunction", 2, issues=[])
    if "                - dynamodb:Scan" in scheduled:
        issues.append("ProofLoopScheduledFunction must query the registry, not Scan")
    index_arn = (
        '              Resource: !Sub '
        '"${ProofLoopEvidenceTable.Arn}/index/AgentRegistryIndex"'
    )
    if scheduled.count(index_arn) != 1:
        issues.append("ProofLoopScheduledFunction requires the registry index ARN")
    if index_arn in api_function:
        issues.append("ProofLoopApiFunction must not access the registry index")
    bedrock_action = "                - bedrock:InvokeModel"
    bedrock_resource = "              Resource: !Ref BedrockModelArn"
    if api_function.count(bedrock_action) != 1:
        issues.append("ProofLoopApiFunction requires exactly one bedrock:InvokeModel action")
    if api_function.count(bedrock_resource) != 1:
        issues.append("ProofLoopApiFunction Bedrock access must use BedrockModelArn")
    if bedrock_action in scheduled:
        issues.append("ProofLoopScheduledFunction must not invoke Bedrock")
    forbidden_actions = ("DeleteItem", "BatchWriteItem", "sqs:")
    for logical_id, function in (
        ("ProofLoopApiFunction", api_function),
        ("ProofLoopScheduledFunction", scheduled),
    ):
        for action in forbidden_actions:
            if action in "\n".join(function):
                issues.append(f"{logical_id} must not grant {action}")


def _validate_schedule(lines: Sequence[str], issues: list[str]) -> None:
    scheduled_function = _find_block(
        lines, "ProofLoopScheduledFunction", 2, issues=[]
    )
    async_invoke = _find_block(scheduled_function, "EventInvokeConfig", 6, issues)
    _expect_value(
        async_invoke,
        "MaximumEventAgeInSeconds",
        8,
        "300",
        issues,
        "ProofLoopScheduledFunction.EventInvokeConfig",
    )
    _expect_value(
        async_invoke,
        "MaximumRetryAttempts",
        8,
        "2",
        issues,
        "ProofLoopScheduledFunction.EventInvokeConfig",
    )
    destination = _find_block(async_invoke, "DestinationConfig", 8, issues)
    on_failure = _find_block(destination, "OnFailure", 10, issues)
    _expect_value(
        on_failure,
        "Type",
        12,
        "SQS",
        issues,
        "ProofLoopScheduledFunction.EventInvokeConfig.OnFailure",
    )
    event = _find_block(scheduled_function, "FiveMinuteReconciliation", 8, issues)
    _expect_value(event, "Type", 10, "Schedule", issues, "FiveMinuteReconciliation")
    _expect_value(
        event,
        "Schedule",
        12,
        "rate(5 minutes)",
        issues,
        "FiveMinuteReconciliation",
    )
    _expect_value(
        event,
        "Enabled",
        12,
        "!If [ReconciliationScheduleEnabled, true, false]",
        issues,
        "FiveMinuteReconciliation",
    )
    retry = _find_block(event, "RetryPolicy", 12, issues)
    _expect_value(
        retry,
        "MaximumEventAgeInSeconds",
        14,
        "300",
        issues,
        "FiveMinuteReconciliation.RetryPolicy",
    )
    _expect_value(
        retry,
        "MaximumRetryAttempts",
        14,
        "2",
        issues,
        "FiveMinuteReconciliation.RetryPolicy",
    )
    dead_letter = _find_block(event, "DeadLetterConfig", 12, issues)
    _expect_value(
        dead_letter,
        "Type",
        14,
        "SQS",
        issues,
        "FiveMinuteReconciliation.DeadLetterConfig",
    )
    _expect_value(
        dead_letter,
        "QueueLogicalId",
        14,
        "ProofLoopScheduledDeadLetterQueue",
        issues,
        "FiveMinuteReconciliation.DeadLetterConfig",
    )


def _validate_log_groups(lines: Sequence[str], issues: list[str]) -> None:
    for logical_id in LOG_GROUPS:
        log_group = _find_block(lines, logical_id, 2, issues)
        _expect_value(
            log_group,
            "Type",
            4,
            "AWS::Logs::LogGroup",
            issues,
            logical_id,
        )
        _expect_value(log_group, "RetentionInDays", 6, "30", issues, logical_id)


def _validate_schedule_condition(lines: Sequence[str], issues: list[str]) -> None:
    _expect_sequence(
        lines,
        (
            "  ReconciliationScheduleEnabled: !Equals",
            "    - !Ref EnableReconciliationSchedule",
            '    - "true"',
        ),
        issues,
        "ReconciliationScheduleEnabled must compare the activation parameter to true",
    )


def _validate_notifications_and_alarms(
    lines: Sequence[str],
    issues: list[str],
) -> None:
    topic = _find_block(lines, "ProofLoopAlarmTopic", 2, issues)
    _expect_value(
        topic,
        "Type",
        4,
        "AWS::SNS::Topic",
        issues,
        "ProofLoopAlarmTopic",
    )
    subscription = _find_block(
        lines, "ProofLoopAlarmEmailSubscription", 2, issues
    )
    _expect_value(
        subscription,
        "Type",
        4,
        "AWS::SNS::Subscription",
        issues,
        "ProofLoopAlarmEmailSubscription",
    )
    for key, expected in (
        ("Protocol", "email"),
        ("Endpoint", "!Ref AlarmNotificationEmail"),
        ("TopicArn", "!Ref ProofLoopAlarmTopic"),
    ):
        _expect_value(
            subscription,
            key,
            6,
            expected,
            issues,
            "ProofLoopAlarmEmailSubscription",
        )

    resources = _find_block(lines, "Resources", 0, issues=[])
    alarm_type = "    Type: AWS::CloudWatch::Alarm"
    if resources.count(alarm_type) != len(ALARM_SPECS):
        issues.append(f"template requires exactly {len(ALARM_SPECS)} alarms")

    for logical_id, (namespace, metric, statistic, dimensions) in ALARM_SPECS.items():
        alarm = _find_block(lines, logical_id, 2, issues)
        _expect_value(
            alarm,
            "Type",
            4,
            "AWS::CloudWatch::Alarm",
            issues,
            logical_id,
        )
        for key, expected in (
            ("ActionsEnabled", "true"),
            ("Namespace", namespace),
            ("MetricName", metric),
            ("Statistic", statistic),
            ("Period", "300"),
            ("EvaluationPeriods", "1"),
            ("Threshold", "1"),
            ("ComparisonOperator", "GreaterThanOrEqualToThreshold"),
            ("TreatMissingData", "notBreaching"),
        ):
            _expect_value(alarm, key, 6, expected, issues, logical_id)
        actions = _find_block(alarm, "AlarmActions", 6, issues)
        _expect_sequence(
            actions,
            ("      AlarmActions:", "        - !Ref ProofLoopAlarmTopic"),
            issues,
            f"{logical_id}.AlarmActions must use ProofLoopAlarmTopic",
        )
        alarm_dimensions = _find_block(alarm, "Dimensions", 6, issues)
        for name, value in dimensions:
            _expect_sequence(
                alarm_dimensions,
                (f"        - Name: {name}", f"          Value: {value}"),
                issues,
                f"{logical_id}.Dimensions must include {name}={value}",
            )


def _validate_resource_budget(lines: Sequence[str], issues: list[str]) -> None:
    resources = _find_block(lines, "Resources", 0, issues)
    for line in resources:
        if _indent(line) != 4 or not line.strip().startswith("Type:"):
            continue
        resource_type = line.split(":", 1)[1].strip()
        if resource_type in FORBIDDEN_RESOURCE_TYPES:
            issues.append(f"prohibited always-on resource type: {resource_type}")


def validate_template(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    issues: list[str] = []
    _expect_value(
        lines,
        "Transform",
        0,
        "AWS::Serverless-2016-10-31",
        issues,
        "template",
    )
    if "proofloop-demo-development-invoices" in "\n".join(lines):
        issues.append(
            "template must not hard-code the assurance boundary "
            "proofloop-demo-development-invoices; inject !Ref AssuranceBoundaryId"
        )
    _validate_parameters(lines, issues)
    _validate_schedule_condition(lines, issues)
    _validate_table(lines, issues)
    _validate_functions(lines, issues)
    _validate_schedule(lines, issues)
    _validate_log_groups(lines, issues)
    _validate_notifications_and_alarms(lines, issues)
    _validate_resource_budget(lines, issues)
    return issues


def validate_makefile(path: Path) -> list[str]:
    contents = path.read_text(encoding="utf-8")
    issues: list[str] = []
    for target in FUNCTIONS:
        marker = f"build-{target}:"
        if sum(line.rstrip() == marker for line in contents.splitlines()) != 1:
            issues.append(f"Makefile must define exactly one {marker}")
    required_fragments = (
        "src/proofloop",
        "ARTIFACTS_DIR",
        'project["project"]["dependencies"]',
    )
    for required in required_fragments:
        if required not in contents:
            issues.append(f"Makefile is missing {required}")
    if '".[dev]"' in contents or "'.[dev]'" in contents:
        issues.append("Lambda build must not install development dependencies")
    return issues


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    infra_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=infra_dir / "template.yaml")
    parser.add_argument(
        "--makefile", type=Path, default=infra_dir / "lambda" / "Makefile"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    missing_files = [
        path for path in (args.template, args.makefile) if not path.is_file()
    ]
    if missing_files:
        print("Missing required infrastructure files:", file=sys.stderr)
        for path in missing_files:
            print(f"- {path}", file=sys.stderr)
        return 1

    issues = validate_template(args.template)
    issues.extend(validate_makefile(args.makefile))
    if issues:
        print("SAM guardrail violations:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print("SAM package guardrails passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
