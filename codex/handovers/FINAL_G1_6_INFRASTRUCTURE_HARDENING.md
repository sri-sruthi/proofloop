# ProofLoop Final G1.6 Infrastructure-Hardening Gate

**Date:** 2026-07-18  
**Track:** G1.6 - approved TDD infrastructure hardening  
**Verdict:** **IMPLEMENTATION AND PRIVATE CI COMPLETE / READY TO REQUEST G2
READ-ONLY PREFLIGHT / AWS EXECUTION NOT AUTHORIZED**  
**Production readiness:** not claimed

## Customer outcome

The three accepted G1.5 infrastructure blockers are closed in the reviewed
private commit:

1. the browser origin is a required, non-wildcard deployment parameter injected
   into the API Lambda;
2. the five-minute reconciliation schedule is explicitly disabled by default;
   and
3. the approved ten development alarms, stack-managed SNS topic, and
   parameterized email subscription are infrastructure as code.

The approved DynamoDB delete-on-stack-removal/retain-on-replacement policy is
also explicit. The stack still hosts no dashboard, the API key remains a
controlled development/demo boundary, and no agent/privacy/domain behavior was
changed.

No AWS API, caller-identity lookup, CloudFormation change set, deployment,
resource, schedule activation, or Bedrock request was made.

## Git and private CI evidence

| Evidence | Exact result |
|---|---|
| Canonical repository | `/Users/srisruthi/Aivar Project` |
| G1.5 documentation checkpoint | `3b0322d6feaf346fac517f911da4af0fcb70dff0` |
| Isolated branch | `codex/track-g1-6-infrastructure-hardening` |
| Implementation commit | `4ae391edcaf38d82017667967c0d3414a1129f6e` |
| Author and committer | `Sri Sruthi Manikka Nagasamy <sruthimanikka@gmail.com>`; no AI author/co-author trailer |
| Remote | `sri-sruthi/proofloop-aivar-private` |
| Visibility before push | GraphQL: `isPrivate=true`, `visibility=PRIVATE`; REST: `private=true`, `visibility=private`; owner `sri-sruthi` |
| CI run | [29649766982](https://github.com/sri-sruthi/proofloop-aivar-private/actions/runs/29649766982), overall `success` |
| Python 3.12 job | [88093978357](https://github.com/sri-sruthi/proofloop-aivar-private/actions/runs/29649766982/job/88093978357), `success`, CPython 3.12.13 |
| Python 3.13 job | [88093978339](https://github.com/sri-sruthi/proofloop-aivar-private/actions/runs/29649766982/job/88093978339), `success`, CPython 3.13.14 on native `aarch64` |

Exact private job-log evidence:

- Python 3.12: structural validator and strict SAM lint passed; `277 passed in
  2.80s`; mypy found no issues in 89 files; Ruff, pip-audit, Bandit,
  compile/import, and dashboard syntax steps succeeded.
- Python 3.13: structural validator and strict SAM lint passed; the explicit
  `aarch64` assertion passed; `Build Succeeded`; `277 passed in 2.23s`; mypy
  found no issues in 89 files; Ruff passed; both built Lambda handlers were
  verified; pip-audit reported no known vulnerabilities; Bandit,
  compile/import, and dashboard syntax steps succeeded.

The workflow has read-only repository contents permission and received no AWS
deployment credentials. Its SAM operations were local validation/build only.

## Files changed

Implementation commit `4ae391e` contains exactly these 11 Codex-owned files:

- `.github/workflows/ci.yml`
- `README.md`
- `docs/PROJECT_RULES.md`
- `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`
- `docs/superpowers/plans/2026-07-18-proofloop-g1-6-infrastructure-hardening.md`
- `docs/superpowers/specs/2026-07-18-proofloop-g1-6-infrastructure-hardening-design.md`
- `infra/README.md`
- `infra/scripts/validate_template.py`
- `infra/template.yaml`
- `tests/integration/test_operational_infra_hardening.py`
- `tests/integration/test_scheduled_hardening.py`

This final evidence update additionally changes:

- `codex/handovers/FINAL_G1_6_INFRASTRUCTURE_HARDENING.md`
- `codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md`
- `README.md`
- `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`

No file under `src/proofloop/agents`, no privacy/domain/application behavior,
no dashboard asset, and no Claude-owned file changed.

## Test-first evidence

The implementation followed focused RED-GREEN cycles:

1. **Origin and schedule RED:** two tests were written against the unchanged
   template; both failed because `AllowedOrigin` and
   `EnableReconciliationSchedule` did not exist. After the minimal parameter,
   condition, environment, and schedule changes, both passed.
2. **Lifecycle, SNS, and alarms RED:** three new tests failed while the two
   origin/schedule tests stayed green. Failures identified absent table
   policies, absent email/topic/subscription, and zero alarms. The narrow
   template additions made all five pass.
3. **Validator RED:** the hardened-template acceptance test and five mutation
   tests were added before validator changes. Six tests failed because the old
   validator rejected the new schedule shape and did not detect origin,
   schedule-default, lifecycle, metric, or alarm-action drift. The validator
   expansion made the mutation tests pass; one remaining inline-condition
   parsing failure was fixed in the validator, not weakened in the test. The
   module then reported 11 passing tests.
4. **Generated logical-ID RED:** strict transformed-template lint showed that
   SAM 1.163.0 generates
   `ProofLoopScheduledFunctionEventInvokeConfigOnFailureQueue`, not the earlier
   assumed suffix. The structural expectation was changed first and failed;
   the template and validator reference were then corrected. Eleven focused
   tests and `sam validate --lint` passed.
5. **CI strict-lint RED:** an expectation that CI run `sam validate --lint`
   failed against the basic-only workflow. The one-line workflow repair made
   the focused test pass.

Final focused result:

```text
python -m pytest -q tests/integration/test_operational_infra_hardening.py
11 passed
```

Final full result: `277 passed` locally and in both private CI jobs.

## Exact infrastructure contract

### Deployment parameters

| Parameter | Contract |
|---|---|
| `ApiKey` | required `String`, `NoEcho`, no default; supply only through an approved secret channel |
| `AllowedOrigin` | required `String`, no default; HTTP(S) pattern rejects `*`; approved first value `http://localhost:8000` |
| `EnableReconciliationSchedule` | `String`, allowed values `true`/`false`, default `false` |
| `AlarmNotificationEmail` | required `String`, `NoEcho`, no default, email-shaped constraint; product owner supplies it at deployment |
| `BedrockModelId` | required string; exact model or inference-profile decision remains open |
| `BedrockModelArn` | required Bedrock ARN; remains open pending G2 model/access discovery |
| `BedrockRegion` | required AWS region string; target `ap-south-1` still needs G2 verification for the chosen model path |
| `MaxModelCalls` | default 2, range 1-10 |
| `MaxModelRetries` | default 1, range 0-9 |
| `MaxOutputTokens` | default/max 2,000 |
| `ModelTimeoutSeconds` | default 30, range 1-40 |

`AllowedOrigin` is injected as `PROOFLOOP_ALLOWED_ORIGIN`. The schedule's
`Enabled` property uses the `ReconciliationScheduleEnabled` condition and
renders false by default. The schedule was not enabled in this track.

### Ten alarms

Every alarm uses period 300 seconds, one evaluation period, threshold 1,
`GreaterThanOrEqualToThreshold`, and `TreatMissingData: notBreaching`. Count
metrics use `Sum`; SQS visible-message depth uses `Maximum`.

| Logical ID | Namespace / metric | Dimension |
|---|---|---|
| `ProofLoopApiErrorsAlarm` | `AWS/Lambda` / `Errors` | API `FunctionName` |
| `ProofLoopApiThrottlesAlarm` | `AWS/Lambda` / `Throttles` | API `FunctionName` |
| `ProofLoopScheduledErrorsAlarm` | `AWS/Lambda` / `Errors` | scheduled `FunctionName` |
| `ProofLoopScheduledThrottlesAlarm` | `AWS/Lambda` / `Throttles` | scheduled `FunctionName` |
| `ProofLoopEventBridgeDeliveryDlqDepthAlarm` | `AWS/SQS` / `ApproximateNumberOfMessagesVisible` | EventBridge DLQ `QueueName` |
| `ProofLoopLambdaFailureDlqDepthAlarm` | `AWS/SQS` / `ApproximateNumberOfMessagesVisible` | Lambda async-failure DLQ `QueueName` |
| `ProofLoopEventBridgeFailedInvocationsAlarm` | `AWS/Events` / `FailedInvocations` | generated schedule `RuleName` |
| `ProofLoopHttpApi5xxAlarm` | `AWS/ApiGateway` / `5xx` | API ID and `$default` stage |
| `ProofLoopDynamoDbReadThrottlesAlarm` | `AWS/DynamoDB` / `ReadThrottleEvents` | evidence `TableName` |
| `ProofLoopDynamoDbWriteThrottlesAlarm` | `AWS/DynamoDB` / `WriteThrottleEvents` | evidence `TableName` |

All alarm actions reference the same-stack `ProofLoopAlarmTopic`. The required
email subscription remains operationally inactive until the product owner
confirms it after deployment.

## Exact resource, IAM, and cost diff

- **Explicit resources:** +12: ten `AWS::CloudWatch::Alarm`, one
  `AWS::SNS::Topic`, and one `AWS::SNS::Subscription`.
- **Existing resources:** the two Lambdas, HTTP API, on-demand table/GSI, three
  30-day log groups, EventBridge rule, and two SQS failure paths remain. No
  dashboard, WAF, Cognito, NAT, ECS, EKS, OpenSearch, Budget, or always-on
  compute resource was added.
- **Table lifecycle:** adds `DeletionPolicy: Delete` and
  `UpdateReplacePolicy: Retain`. Stack deletion loses current table data;
  replacement protects the old table but can leave a billable orphan requiring
  separately approved cleanup.
- **IAM:** zero new policy statements and zero new Lambda actions. The staged
  diff contained no added `Action`, `bedrock:`, `dynamodb:`, `logs:`, or `sns:`
  permission line. Neither Lambda gains SNS/CloudWatch permissions; alarm-to-SNS
  publication uses the AWS service integration.
- **Costs:** ten standard alarm metric-hours accrue while the stack exists.
  SNS adds state-change request/delivery usage. The topic/subscription have no
  always-on compute. The disabled schedule avoids normal recurring Lambda,
  DynamoDB, EventBridge, log, and failure-path usage before smoke. A retained
  replacement table can continue storage/read charges until removed. Existing
  pay-per-use API/Lambda/DynamoDB/SQS/log/SAM-artifact and separately authorized
  Bedrock costs remain.

## Complete local gate

Disposable application gate: CPython 3.13.7, pytest 9.1.1, pip 26.1.2.

```text
python -m pip check
  -> No broken requirements found.
python -m pytest -q
  -> 277 passed in 1.91s; staged pre-commit repeat: 277 passed in 1.66s
python -m mypy src/proofloop tests
  -> Success: no issues found in 89 source files
python -m ruff check src tests scripts infra/scripts
  -> All checks passed!
python -m bandit -q -r src/proofloop
  -> exit 0, no findings
python -m pip_audit --strict --progress-spinner off
  -> No known vulnerabilities found
python -m compileall -q src tests scripts infra/scripts
  -> exit 0
python scripts/demo_proofloop.py
  -> exit 0; GREEN -> AMBER -> RED -> AMBER -> GREEN
python scripts/demo_agent_to_compliance.py
  -> exit 0; bounded privacy/failure/conflict/canary/recovery scenes passed
python infra/scripts/validate_template.py
  -> SAM package guardrails passed.
node --check dashboard/app.js
  -> exit 0
source handler imports
  -> Imported 2 source handlers.
import-isolation, dangerous-code, credential-shape, and environment scans
  -> no prohibited imports/code/key shapes; only tracked `.env.example`
git diff --cached --check
  -> exit 0
```

Disposable SAM CLI 1.163.0 gate:

```text
sam validate --lint --template-file infra/template.yaml
  -> valid SAM template; exit 0
PYTHON=<CPython-3.13.7> sam build --template-file infra/template.yaml
  -> Build Succeeded
python infra/scripts/verify_built_handlers.py <API artifact> ... <scheduled artifact> ...
  -> Verified 2 built Lambda handlers.
artifact secret/cache scan
  -> no .env, credential/key shape, test cache, or development toolchain
```

The first native build inherited macOS Python 3.12 and produced a CPython 3.12
`pydantic-core` wheel, which the 3.13 artifact verifier correctly rejected.
Supplying the Makefile's existing `PYTHON` override as CPython 3.13.7 fixed the
environment mismatch without a repository code change. Private ARM64 Linux CI
then independently built/imported the artifacts with CPython 3.13.14.

## Security-tooling advisory

The application/project-only strict audit is green locally and in both CI jobs.
A deliberately separate audit of pip-installed AWS SAM CLI 1.163.0 reports:

```text
click 8.1.8  PYSEC-2026-2132  fixed in 8.3.3
```

The advisory is command injection through `click.edit()`. SAM CLI 1.163.0 is
the newest available release and pins `click==8.1.8`; overriding it would break
the declared tool environment, so the finding was not suppressed. A source scan
found no direct `click.edit` call in installed `samcli`, and the commands used
here were controlled offline validate/build inputs, but this remains an
upstream toolchain advisory. Before G2 creates a change set, prefer an updated
SAM release that permits Click 8.3.3+ or explicitly review/accept a narrowly
isolated alternative. This finding does not affect the packaged Lambda runtime,
which contains only ProofLoop and Pydantic dependencies.

## Remaining blockers and human decisions

G1.6 closes the code/template blockers. The following remain before a
non-executed change set can be created or executed:

1. separately authorize G2 and verify the exact AWS caller account/role;
2. approve the stack name and verify `ap-south-1` for the selected Bedrock
   model/inference-profile path;
3. select the exact model/profile ID and least-privilege invocation ARN;
4. select an audited/fixed SAM CLI or explicitly accept the isolated upstream
   Click advisory for the non-executed change-set command;
5. supply, without recording, the high-entropy API key and alarm email; confirm
   the email subscription before execution;
6. record budget amount/thresholds/recipients, CloudWatch and both DLQ owners,
   replay runbook, rollback authority, and retained-table cleanup owner;
7. record tenant, environment, assurance-boundary, synthetic smoke, retention,
   and rollback evidence decisions; and
8. inspect the generated change set for exact parameters, disabled schedule,
   table replacement/deletion impact, IAM, resources, artifacts, and costs.

After deployment—but before schedule activation—health, authentication,
persistence, privacy, canary, both DLQs, all alarm actions, notification
delivery, and rollback smoke must pass. The dashboard remains local. A real
Bedrock request and schedule activation each require separate later approval.

## G2 readiness verdict

**READY to request and begin a separately authorized G2 read-only
identity/model preflight.** The G1.6 implementation, local gate, and private
Python 3.12/3.13 CI/SAM gate are complete.

**NOT YET READY to create the non-executed change set** until G2 resolves the
caller/model/ARN/stack/parameter/owner/budget inputs and selects or explicitly
accepts the isolated SAM tooling path above. It is not ready to execute a change
set, deploy, invoke Bedrock, enable the schedule, or claim production readiness.

## Five files for human inspection

1. `infra/template.yaml`
2. `tests/integration/test_operational_infra_hardening.py`
3. `infra/scripts/validate_template.py`
4. `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`
5. `.github/workflows/ci.yml`

## Recommended next prompt

Authorize Track G2 separately and preserve its split gate: read-only AWS
identity/model discovery first; only after mandatory inputs are recorded may it
create one non-executed CloudFormation change set. Do not execute it, invoke
Bedrock, enable the schedule, or create any other AWS resource.
