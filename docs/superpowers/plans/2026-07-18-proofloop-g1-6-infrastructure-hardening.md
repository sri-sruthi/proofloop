# ProofLoop Track G1.6 Infrastructure Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the allowed-origin, initially enabled schedule, alarm, notification, and DynamoDB lifecycle blockers with a test-first SAM template change that remains offline until a later Track G2.

**Architecture:** Keep application/domain behavior unchanged and enforce the deployment boundary entirely in the SAM template plus its credential-free validator. Reference SAM's stable generated logical IDs for the existing schedule rule and two failure queues, add a stack-managed SNS email path, and use explicit CloudFormation parameters/conditions so reviewers can see every first-deployment decision.

**Tech Stack:** AWS SAM/CloudFormation YAML, Python 3.13, pytest 9, the repository's text-structural validator, GitHub Actions, AWS SAM CLI 1.163.x.

## Global Constraints

- Do not call AWS, create a CloudFormation change set, deploy, invoke Bedrock, enable the schedule, or create an AWS resource.
- Do not edit agent/privacy behavior, domain verdict semantics, dashboard code/hosting, customer identity, WAF, Cognito, NAT, ECS, EKS, OpenSearch, or unrelated functionality.
- `AllowedOrigin` is required, has no default, rejects wildcard values, and is supplied as `http://localhost:8000` only in deployment documentation.
- `EnableReconciliationSchedule` defaults to string `false`; the rendered SAM `Enabled` value is a Boolean selected through a CloudFormation condition.
- The ten approved alarms use period 300, evaluation periods 1, threshold 1, greater-than-or-equal comparison, and missing data not breaching.
- Count metrics use Sum; SQS visible-message gauges use Maximum.
- `AlarmNotificationEmail` is required, has no default, is `NoEcho`, and no real address is committed.
- The stack creates one SNS topic and one email subscription; the product owner is the initial development responder and must confirm the subscription later.
- The evidence table uses `DeletionPolicy: Delete` and `UpdateReplacePolicy: Retain`; log retention remains 30 days.
- Preserve API-key authentication and classify it as controlled development/demo only.
- Commit/push only after every local gate passes, and only to the existing verified-private remote with the user's personal Git identity and no AI author/co-author trailer.

---

### Task 1: Add RED tests for origin and schedule contracts

**Files:**
- Create: `tests/integration/test_operational_infra_hardening.py`
- Test: `tests/integration/test_operational_infra_hardening.py`

**Interfaces:**
- Consumes: raw `infra/template.yaml` text.
- Produces: `_block(name)` and `_parameter_pattern(name)` helpers plus structural contracts for later template changes.

- [ ] **Step 1: Write the focused tests before editing the template**

Create a module-level `TEMPLATE` string and a `_block(name: str) -> str` helper
that returns one two-space-indented parameter/resource/condition block. Add:

```python
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
```

- [ ] **Step 2: Run the focused tests and capture RED**

Run:

```bash
/tmp/proofloop-g1-6.xaAazr/venv/bin/python -m pytest \
  tests/integration/test_operational_infra_hardening.py -q
```

Expected: both tests fail because the two parameters, condition, and API
environment injection do not exist and the schedule still says `Enabled: true`.

### Task 2: Implement origin and disabled-first schedule

**Files:**
- Modify: `infra/template.yaml`
- Test: `tests/integration/test_operational_infra_hardening.py`

**Interfaces:**
- Produces: `AllowedOrigin`, `EnableReconciliationSchedule`,
  `ReconciliationScheduleEnabled`, `PROOFLOOP_ALLOWED_ORIGIN`, and the conditional
  schedule Boolean.

- [ ] **Step 1: Add the minimal parameters and condition**

Add the exact parameter/condition contract from
`docs/superpowers/specs/2026-07-18-proofloop-g1-6-infrastructure-hardening-design.md`.
Use double-quoted `"false"`/`"true"` values in the template so the structural
contract is unambiguous.

- [ ] **Step 2: Inject the origin and replace the hard-coded schedule state**

Add:

```yaml
PROOFLOOP_ALLOWED_ORIGIN: !Ref AllowedOrigin
```

to the API environment and replace `Enabled: true` with:

```yaml
Enabled: !If [ReconciliationScheduleEnabled, true, false]
```

- [ ] **Step 3: Run focused tests and verify GREEN**

Run the Task 1 command. Expected: two tests pass.

### Task 3: Add RED tests for table lifecycle, SNS, and ten alarms

**Files:**
- Modify: `tests/integration/test_operational_infra_hardening.py`
- Test: `tests/integration/test_operational_infra_hardening.py`

**Interfaces:**
- Produces: exact logical-ID, metric, statistic, dimension, threshold, action,
  and lifecycle expectations consumed by the template and validator tasks.

- [ ] **Step 1: Add the table and SNS tests**

```python
def test_table_lifecycle_is_explicit_for_controlled_development() -> None:
    table = _block("ProofLoopEvidenceTable")
    assert "    DeletionPolicy: Delete" in table
    assert "    UpdateReplacePolicy: Retain" in table


def test_alarm_email_is_required_and_stack_managed() -> None:
    email = _block("AlarmNotificationEmail")
    assert "    Type: String" in email
    assert "    NoEcho: true" in email
    assert "    Default:" not in email
    assert "AWS::SNS::Topic" in _block("ProofLoopAlarmTopic")
    subscription = _block("ProofLoopAlarmEmailSubscription")
    assert "AWS::SNS::Subscription" in subscription
    assert "Protocol: email" in subscription
    assert "Endpoint: !Ref AlarmNotificationEmail" in subscription
    assert "TopicArn: !Ref ProofLoopAlarmTopic" in subscription
```

- [ ] **Step 2: Add one data-driven alarm test**

Define exact alarm cases for the ten logical IDs in the approved design. For
each block assert:

```python
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
```

Also assert `TEMPLATE.count("Type: AWS::CloudWatch::Alarm") == 10`.

- [ ] **Step 3: Run the focused tests and capture RED**

Expected: the origin/schedule tests remain green; lifecycle, SNS, and alarm
tests fail because those resources are absent.

### Task 4: Implement table lifecycle, notifications, and alarms

**Files:**
- Modify: `infra/template.yaml`
- Test: `tests/integration/test_operational_infra_hardening.py`

**Interfaces:**
- Produces: twelve new explicit resources and the lifecycle attributes without
  changing either Lambda role.

- [ ] **Step 1: Add the table lifecycle and email parameter**

Add `DeletionPolicy: Delete` and `UpdateReplacePolicy: Retain` at resource
attribute indentation. Add the required, `NoEcho`, no-default
`AlarmNotificationEmail` parameter with the approved email pattern.

- [ ] **Step 2: Add the topic and subscription**

```yaml
ProofLoopAlarmTopic:
  Type: AWS::SNS::Topic
  Properties:
    Tags:
      - Key: Service
        Value: ProofLoop

ProofLoopAlarmEmailSubscription:
  Type: AWS::SNS::Subscription
  Properties:
    Protocol: email
    Endpoint: !Ref AlarmNotificationEmail
    TopicArn: !Ref ProofLoopAlarmTopic
```

- [ ] **Step 3: Add the ten exact alarm resources**

Use the logical IDs, namespaces, metrics, statistics, and dimensions in the
approved design. Every alarm contains the common properties below:

```yaml
ActionsEnabled: true
AlarmActions:
  - !Ref ProofLoopAlarmTopic
ComparisonOperator: GreaterThanOrEqualToThreshold
EvaluationPeriods: 1
Period: 300
Threshold: 1
TreatMissingData: notBreaching
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Expected: every test in `test_operational_infra_hardening.py` passes.

- [ ] **Step 5: Prove IAM did not expand**

Run:

```bash
git diff -- infra/template.yaml | rg -n "Action:|bedrock:|dynamodb:|logs:|sns:"
```

Expected: no added Lambda policy action and no `sns:*` IAM permission.

### Task 5: Add RED validator mutation tests and harden the validator

**Files:**
- Modify: `tests/integration/test_operational_infra_hardening.py`
- Modify: `infra/scripts/validate_template.py`
- Test: `tests/integration/test_operational_infra_hardening.py`

**Interfaces:**
- Consumes: hardened template text plus `--template`/`--makefile` validator CLI.
- Produces: credential-free rejection of origin, schedule, lifecycle,
  notification, and alarm drift.

- [ ] **Step 1: Add a subprocess helper and parameterized negative test**

Create `_run_validator(tmp_path, template) -> subprocess.CompletedProcess[str]`
using the repository validator and copied Makefile. Parameterize mutations for:

- origin injection changed to `PROOFLOOP_ALLOWED_ORIGIN: "*"`;
- schedule default changed from `"false"` to `"true"`;
- `UpdateReplacePolicy: Retain` changed to `Delete`;
- one alarm metric changed from `Errors` to `Invocations`; and
- one alarm action changed away from `ProofLoopAlarmTopic`.

Assert exit 1 and the relevant logical ID/property in stderr.

- [ ] **Step 2: Run the negative test and capture RED**

Expected: mutations return exit 0 because the existing validator does not yet
know the G1.6 contracts.

- [ ] **Step 3: Extend validator constants and focused functions**

Add `ALARM_SPECS`, `_validate_notifications_and_alarms`, and new checks in
`_validate_parameters`, `_validate_table`, `_validate_functions`, and
`_validate_schedule`. Call the new function from `validate_template`.

- [ ] **Step 4: Verify negative and full focused tests GREEN**

Run the full operational-hardening module and
`python infra/scripts/validate_template.py`. Expected: all focused tests pass and
the validator prints `SAM package guardrails passed.`

### Task 6: Update deployment, cost, rollback, and release documentation

**Files:**
- Modify: `infra/README.md`
- Modify: `README.md`
- Modify: `docs/PROJECT_RULES.md`
- Modify: `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`
- Modify: `codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md`

**Interfaces:**
- Consumes: final template parameter/resource names and approved decisions.
- Produces: reviewer/deployer instructions without real account, ARN, key, or
  email values.

- [ ] **Step 1: Update infrastructure README**

Document the twelve resources, ten alarm metrics, pending email confirmation,
disabled-first schedule, local dashboard, controlled API-key boundary, and
delete-versus-retain table trade-off. Update the non-executed parameter example
to include:

```text
AllowedOrigin=http://localhost:8000
AlarmNotificationEmail=$PROOFLOOP_ALARM_EMAIL
EnableReconciliationSchedule=false
```

- [ ] **Step 2: Reconcile root/project status**

Replace the three G1.5 blockers with G1.6 implementation status while retaining
the no-AWS/no-Bedrock/no-production claim. Correct `docs/PROJECT_RULES.md` so it
records local Python 3.13 and private Python 3.12/3.13 CI evidence.

- [ ] **Step 3: Reconcile checklist and G1.5 addendum**

Mark only the implemented local controls closed after local verification. Keep
AWS identity/model, email confirmation, budget, owners, change set, deployment,
smoke, schedule activation, rollback, and Bedrock items unchecked. Add a G1.6
resolution addendum to the G1.5 review without rewriting its historical
findings.

### Task 7: Run the complete clean local gate

**Files:**
- Verify: all changed files and built artifacts

- [ ] **Step 1: Run Python and security gates**

Run `pip check`, pytest, mypy, Ruff, Bandit, strict pip-audit, and compileall in
a clean project-only Python 3.13 environment. Keep SAM CLI in its separate
disposable tool environment so the application audit is not conflated with
SAM's own dependency graph; report any SAM-tool finding separately.

- [ ] **Step 2: Run behavior/package gates**

Run both demos, template validator, dashboard syntax, source-handler imports,
all existing import-isolation/privacy/secret/dangerous-code scans, `sam
validate`, native `sam build`, and the two built-handler imports.

- [ ] **Step 3: Inspect the complete proposed commit**

Run diff whitespace/scope checks, staged manifest/size review, AWS/private-key/
token/email/customer-data scan, and verify no Claude-owned file or dashboard/
agent/domain source changed.

### Task 8: Commit, push privately, and inspect CI

**Files:**
- Create: `codex/handovers/FINAL_G1_6_INFRASTRUCTURE_HARDENING.md`
- Verify: `.github/workflows/ci.yml` execution only; do not edit unless a
  diagnosed CI-only defect is within Codex ownership.

- [ ] **Step 1: Verify remote privacy before push**

Use both `gh repo view` and the GitHub REST repository view; require
`isPrivate: true`, `visibility: PRIVATE/private`, and owner `sri-sruthi`.

- [ ] **Step 2: Commit and push the implementation branch**

Use the personal Git identity already configured. Include no Codex/Claude/bot
author or co-author trailer. Push only
`codex/track-g1-6-infrastructure-hardening` to `origin`.

- [ ] **Step 3: Inspect actual CI logs**

Wait for both Python 3.12 and native ARM64 Python 3.13 jobs. Capture run URL,
head SHA, job conclusions, pytest counts, SAM validate/build, and built-handler
results. Diagnose any failure before editing.

- [ ] **Step 4: Produce the final handoff**

Record files changed, RED/GREEN evidence, resource/IAM/cost diff, all local
commands/results, private CI evidence, parameters, unresolved blockers, and an
explicit G2 ready/not-ready verdict. Do not claim AWS or production readiness.
