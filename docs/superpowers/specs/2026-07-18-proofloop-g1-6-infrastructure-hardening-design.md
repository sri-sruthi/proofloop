# ProofLoop Track G1.6 Infrastructure Hardening Design

**Date:** 2026-07-18  
**Status:** approved by the product owner  
**Scope:** SAM infrastructure, structural tests/validator, and deployment documentation only

## Goal and release boundary

Close the three Track G1.5 infrastructure blockers before any AWS preflight or
CloudFormation change set is created:

1. make the browser origin explicit and non-wildcard;
2. make the first-deployment reconciliation schedule disabled by default; and
3. provision the approved ten development alarms with a stack-managed SNS email
   notification path.

This design does not authorize an AWS call, change set, deployment, Bedrock
request, schedule activation, or resource creation. It does not claim
production readiness.

## Approved product decisions

- The controlled-demo origin is `http://localhost:8000`. The template exposes a
  required `AllowedOrigin` string parameter with no default and an allowed
  pattern that rejects `*` and non-HTTP(S) values. Deployment examples pass the
  approved localhost origin explicitly.
- The template exposes `EnableReconciliationSchedule` as a constrained string
  parameter with allowed values `true` and `false`, default `false`. A
  CloudFormation condition converts it to a Boolean for the SAM schedule's
  `Enabled` property.
- Every alarm uses a 300-second period, one evaluation period, a threshold of
  one, `GreaterThanOrEqualToThreshold`, and `TreatMissingData: notBreaching`.
- Count metrics use `Statistic: Sum`. The SQS visible-message depth gauges use
  `Statistic: Maximum`, so one visible message at any point in the period is
  sufficient to alarm.
- The stack creates one SNS topic and one email subscription. The required
  `AlarmNotificationEmail` parameter has no default and is `NoEcho`; no real
  email address is stored in Git. The product owner supplies and confirms the
  subscription during a later authorized deployment.
- The DynamoDB table declares `DeletionPolicy: Delete` and
  `UpdateReplacePolicy: Retain`.
- Existing 30-day log retention remains unchanged.
- The dashboard remains local-only after backend smoke. The current API-key
  boundary remains unchanged and is documented as controlled development/demo
  authentication, not production identity.

## Template contracts

### Parameters and condition

`infra/template.yaml` adds:

```yaml
AllowedOrigin:
  Type: String
  AllowedPattern: '^https?://[^*\s]+$'
  ConstraintDescription: Must be one explicit HTTP(S) origin without a wildcard.
  Description: Required exact browser origin allowed by the ProofLoop API.
AlarmNotificationEmail:
  Type: String
  NoEcho: true
  AllowedPattern: '^[^@\s]+@[^@\s]+\.[^@\s]+$'
  ConstraintDescription: Must be one valid notification email address.
  Description: Required email endpoint for development alarm notifications.
EnableReconciliationSchedule:
  Type: String
  Default: 'false'
  AllowedValues:
    - 'true'
    - 'false'
  Description: Enable only through a reviewed post-smoke stack update.

Conditions:
  ReconciliationScheduleEnabled: !Equals
    - !Ref EnableReconciliationSchedule
    - 'true'
```

The API Lambda receives:

```yaml
PROOFLOOP_ALLOWED_ORIGIN: !Ref AllowedOrigin
```

The schedule receives a real Boolean from:

```yaml
Enabled: !If [ReconciliationScheduleEnabled, true, false]
```

### Table lifecycle

The table resource adds top-level CloudFormation attributes:

```yaml
DeletionPolicy: Delete
UpdateReplacePolicy: Retain
```

Deleting the stack therefore deletes the table and its controlled-development
data. Replacing the table retains the old physical table, which protects
evidence during a risky update but leaves an orphaned billable table requiring
explicit cleanup approval.

### SNS resources

The template creates:

- `ProofLoopAlarmTopic` (`AWS::SNS::Topic`); and
- `ProofLoopAlarmEmailSubscription` (`AWS::SNS::Subscription`) with
  `Protocol: email`, `Endpoint: !Ref AlarmNotificationEmail`, and
  `TopicArn: !Ref ProofLoopAlarmTopic`.

All ten alarms set `ActionsEnabled: true` and use the topic ARN in
`AlarmActions`. No topic policy or Lambda IAM permission is added. Email
delivery remains pending until the product owner confirms the subscription.

### Alarm resources

| Logical ID | Namespace / metric | Statistic | Dimensions |
|---|---|---|---|
| `ProofLoopApiErrorsAlarm` | `AWS/Lambda` / `Errors` | Sum | `FunctionName: !Ref ProofLoopApiFunction` |
| `ProofLoopApiThrottlesAlarm` | `AWS/Lambda` / `Throttles` | Sum | API function name |
| `ProofLoopScheduledErrorsAlarm` | `AWS/Lambda` / `Errors` | Sum | scheduled function name |
| `ProofLoopScheduledThrottlesAlarm` | `AWS/Lambda` / `Throttles` | Sum | scheduled function name |
| `ProofLoopEventBridgeDeliveryDlqDepthAlarm` | `AWS/SQS` / `ApproximateNumberOfMessagesVisible` | Maximum | `QueueName: !GetAtt ProofLoopScheduledDeadLetterQueue.QueueName` |
| `ProofLoopLambdaFailureDlqDepthAlarm` | `AWS/SQS` / `ApproximateNumberOfMessagesVisible` | Maximum | `QueueName: !GetAtt ProofLoopScheduledFunctionEventInvokeConfigOnFailureQueue.QueueName` |
| `ProofLoopEventBridgeFailedInvocationsAlarm` | `AWS/Events` / `FailedInvocations` | Sum | `RuleName: !Ref ProofLoopScheduledFunctionFiveMinuteReconciliation` |
| `ProofLoopHttpApi5xxAlarm` | `AWS/ApiGateway` / `5xx` | Sum | `ApiId: !Ref ProofLoopHttpApi`, `Stage: $default` |
| `ProofLoopDynamoDbReadThrottlesAlarm` | `AWS/DynamoDB` / `ReadThrottleEvents` | Sum | `TableName: !Ref ProofLoopEvidenceTable` |
| `ProofLoopDynamoDbWriteThrottlesAlarm` | `AWS/DynamoDB` / `WriteThrottleEvents` | Sum | table name |

The generated logical IDs are stable SAM contracts for this template shape:

- the schedule rule is
  `ProofLoopScheduledFunctionFiveMinuteReconciliation`;
- its delivery DLQ uses the explicitly supplied
  `ProofLoopScheduledDeadLetterQueue` logical ID; and
- the Lambda asynchronous OnFailure queue is
  `ProofLoopScheduledFunctionEventInvokeConfigOnFailureQueue`.

Tests and the credential-free validator enforce these exact references so an
alarm cannot silently watch a nonexistent metric dimension.

## Resource, IAM, and cost effect

The explicit template resource count increases by twelve: ten standard
CloudWatch metric alarms, one SNS topic, and one email subscription. SAM's two
existing SQS failure queues and EventBridge rule remain generated as before.

There is no new IAM statement. CloudWatch alarm actions publish to the
same-stack SNS topic through the service integration; neither Lambda role gains
SNS, CloudWatch, SQS, dashboard, identity, or network permissions.

Cost effects are limited to ten standard alarm metric-hours plus SNS
notification requests/delivery when state changes. The topic and unconfirmed
email subscription have no always-on compute. The schedule remains disabled by
default, avoiding its recurring Lambda, DynamoDB, log, and failure-path usage
until a reviewed update. A retained replacement table can continue incurring
storage/read costs until an owner explicitly removes it.

## Failure and rollback behavior

- Missing required origin or email values stop parameterized deployment/change-
  set creation rather than selecting an invisible default.
- Wildcard/non-HTTP(S) origins fail parameter validation.
- The initial schedule renders disabled even when the parameter is omitted.
- An unconfirmed email subscription prevents email delivery; deployment
  documentation treats subscription confirmation and alarm delivery testing as
  pre-execution/post-deploy gates.
- Any alarm metric/dimension drift fails structural tests and the offline
  validator before CI can pass.
- Stack deletion deletes the active table; operators must export approved data
  first. Table replacement retains the old table; cleanup is a separately
  approved destructive action.
- Rollback keeps the schedule disabled, restores the exact reviewed template,
  and verifies topic/subscription/alarm state before later activation.

## Test strategy

1. Add focused structural tests before template changes and capture their
   expected failures for missing parameters/resources/policies.
2. Implement only the template behavior needed to make those tests pass.
3. Add negative validator regression tests that mutate the hardened template
   and prove unsafe origin, enabled-by-default schedule, alarm drift, missing
   action, or lifecycle drift is rejected.
4. Update the validator minimally and rerun focused tests.
5. Update `infra/README.md`, root `README.md`, the deployment checklist, and the
   G1.5 review status without adding real parameter values.
6. Run the full Python/security/privacy/isolation/SAM/build/handler/demo gates
   in a disposable Python 3.13 environment, then push only to the existing
   verified-private remote and inspect both CI jobs.

## Out of scope

No agent/privacy/domain behavior, dashboard hosting, Cognito, WAF, customer IAM,
Secrets Manager, NAT, ECS, EKS, OpenSearch, additional alarms, budget resource,
AWS preflight, CloudFormation change set, deployment, schedule activation, or
Bedrock invocation is included.
