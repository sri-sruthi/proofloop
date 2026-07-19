# ProofLoop Post-Activation Deployment and Rollback Checklist

**Status:** G1.5 is offline-reviewed and the approved G1.6 infrastructure
hardening and its private CI gate are complete but deliberately **not
executed**. Python 3.13, SAM, the strictly private Git baseline, and private
Python 3.12/3.13 CI pass for G1.6 commit `4ae391e`; G2 remains separately gated
before the final non-executed change set.  
**Account fact:** payment verification is complete and Lambda is accessible in
`ap-south-1`, as stated by the product owner; no Track G1.5 AWS call verified
the account or region.  
**Trigger order:** G1.6 local/private CI is complete. Next, separately authorize
G2 read-only AWS preflight and, only after its inputs are resolved, one
non-executed change set. Execution and real-model smoke require later, distinct
approval.  
**Rule:** a checked box requires captured evidence; do not infer success from
template or workflow-file presence.

## 1. Human decisions and named owners

Record these in the release ticket before any command runs.

- [ ] **AWS account and region:** account alias/ID (do not paste credentials)
  and one approved region: `________________`.
- [ ] **Stack name:** DNS/CloudFormation-safe name: `________________`.
- [ ] **Bedrock identifier:** exact model ID or inference-profile ID:
  `________________`.
- [ ] **Bedrock IAM resource:** exact invoke-model or inference-profile ARN:
  `________________`.
- [ ] **Model/ARN validation owner:** `________________`; confirms region,
  account/marketplace access, supported invocation mode, and least privilege.
- [ ] **Secure API-key owner:** `________________`; generates a high-entropy key,
  delivers it through the approved secret channel, and confirms it never enters
  Git, `samconfig.toml`, logs, screenshots, tickets, or shell history.
- [x] **Browser origin:** `http://localhost:8000` is approved for the controlled
  demo and implemented as a required parameter; use no wildcard. A hosted
  dashboard requires its separately approved HTTPS origin.
- [x] **Dashboard strategy:** no hosting for backend smoke, then the existing
  local dashboard. No hosted dashboard resource belongs in the initial stack.
- [x] **Initial schedule state:** `DISABLED` is explicitly approved and is the
  parameter default. Enabling later requires a reviewed stack update after
  every smoke/owner gate passes.
- [ ] **Tenant ID:** `________________`.
- [ ] **Environment:** `DEVELOPMENT`, `STAGING`, or approved alternative:
  `________________`.
- [x] **Assurance-boundary ID:** required CloudFormation parameter
  `AssuranceBoundaryId` (no default, no wildcard/blank); injected into both
  Lambda functions as `PROOFLOOP_DEMO_BOUNDARY_ID`. Approved
  controlled-development value: `proofloop-demo-dev-invoices`. The template no
  longer hard-codes any boundary, so a deployment cannot silently certify the
  wrong customer boundary.
- [ ] **Monthly budget and thresholds:** amount `________`; notification
  recipients `________________`; anomaly and hard-stop policy `________________`.
- [x] **CloudWatch/log policy:** 30-day retention is approved. The product owner
  is the initial development responder; operational evidence still needs the
  deploy-time identity and confirmation below.
- [x] **Essential alarm defaults:** period 300 seconds, one evaluation period,
  threshold at least one event/message, and missing data non-breaching are
  approved and implemented.
- [x] **Alarm notification design:** stack-managed SNS topic plus a required
  email-subscription parameter is approved and implemented. No address is
  committed. **Execution remains blocked** until the product owner securely
  supplies the address and confirms the subscription.
- [ ] **EventBridge delivery DLQ owner:** `________________`.
- [ ] **Lambda on-failure DLQ owner:** `________________`.
- [ ] **DLQ inspection/replay runbook:** approved location `________________`.
- [ ] **Rollback authority:** `________________`; may disable schedule, roll back
  code/config, export required evidence, or delete the stack.
- [x] **DynamoDB deletion/replacement policy:** `DeletionPolicy: Delete` and
  `UpdateReplacePolicy: Retain` are approved and implemented for controlled
  development. Stack deletion loses current-table data; replacement retains a
  potentially billable orphan that needs a named cleanup decision.
- [x] **Private GitHub baseline:** `sri-sruthi/proofloop-aivar-private` was
  conclusively verified `PRIVATE`; F2 author/visibility evidence is recorded.
- [x] **Private CI gate:** run `29640732187` passed Python 3.12 and native ARM64
  Python 3.13 without deployment credentials.
- [x] **G1.6 private CI gate:** run `29649766982` passed the hardened commit on
  CPython 3.12.13 and native ARM64 CPython 3.13.14 with 277 tests in each job,
  strict SAM lint, target build/import, audit, Bandit, mypy, Ruff,
  compile/import, and dashboard syntax.
- [ ] **Future deploy authorization:** secrets/OIDC approach, protected
  environment, required checks, deploy approvers, and allowed collaborators are
  recorded before any execution workflow exists.

## 2. Closed local gates and required G1.6 hardening

- [x] RUFF-01: authorized owners removed the unused agent import and replaced
  the two assigned infrastructure lambdas with typed named functions; exact CI
  Ruff command exits zero.
- [x] BANDIT-01: both public assurance `PASS` literals retain their serialized
  contract and carry narrow, documented line-level B105 suppressions; the exact
  Bandit command exits zero without a global disable.
- [x] AUDIT-01: pytest 9 compatibility passed; the dev policy is
  `pytest>=9.0.3,<10`; strict audit reports no known vulnerabilities in the
  clean disposable environment after its bootstrap pip was upgraded.
- [x] The independent agent/privacy audit was received and triaged; optional
  O1/O2 were not implemented and the ownership boundary was preserved.
- [x] A user-authored baseline and conclusively private remote exist; the review
  history is auditable.
- [x] Local Python 3.13, SAM validation/native build, built-handler verification,
  and private Python 3.12/3.13 CI completed with captured evidence. The failed
  local Docker attempt is not claimed; target ARM64 evidence comes from the
  successful native ARM64 Linux CI job.
- [x] **ORIGIN-01:** TDD adds an explicit required `AllowedOrigin`
  deployment parameter and inject `PROOFLOOP_ALLOWED_ORIGIN` into the API
  Lambda. Approve the exact value; do not rely on the application's invisible
  localhost fallback and do not use `*`.
- [x] **SCHEDULE-01:** TDD adds an explicit activation parameter with the
  reconciliation schedule disabled by default. The initial change set must show
  it disabled.
- [x] **ALARMS-01:** TDD defines the approved ten-alarm development set, a
  stack-managed SNS topic, and a required deploy-time email subscription.
- [x] **DATA-POLICY-01:** TDD verifies explicit delete-on-stack-removal and
  retain-on-replacement table behavior.
- [x] The complete local and private Python 3.12/3.13 CI/SAM gate passes again
  after G1.6; no AWS preflight or change-set creation begins before it does.

Detailed design and classification:
`codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md`.

## 3. Read-only account and model preflight

These commands contact AWS but do not create resources. Run only in separately
authorized Track G2, after G1.6 is committed to the private repository and its
complete CI/SAM gate passes.

```bash
aws sts get-caller-identity
aws configure get region
aws bedrock list-foundation-models --region "$PROOFLOOP_BEDROCK_REGION"
```

- [ ] Caller identity matches the approved account and deployment role.
- [ ] Chosen region matches `BedrockRegion` and supports the chosen model or
  inference profile.
- [ ] Model access/marketplace terms are satisfied.
- [ ] The exact ARN satisfies the template pattern and is the single resource
  granted `bedrock:InvokeModel`.
- [ ] No long-lived AWS secret is exported or recorded.

## 4. Reproduce the clean local gate

Track F2 passed this gate with 266 tests. Track G1.6 reran it in a clean
project-only CPython 3.13.7 environment with pytest 9.1.1 and 277 tests; strict
audit reports no known project/tooling vulnerabilities in that environment.
SAM CLI remains separately isolated because version 1.163.0 pins Click 8.1.8,
which the current audit index flags as `PYSEC-2026-2132`.

```bash
python3.13 -m venv /tmp/proofloop-predeploy-venv
source /tmp/proofloop-predeploy-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]" "pip-audit>=2.7,<3" "bandit>=1.7,<2"
python -m pip check
python -m pytest -q
python -m mypy src/proofloop tests
python -m ruff check src tests
python -m bandit -q -r src/proofloop
python -m pip_audit --strict --progress-spinner off
python -m compileall -q src tests scripts infra/scripts
python scripts/demo_proofloop.py
python scripts/demo_agent_to_compliance.py
python infra/scripts/validate_template.py
node --check dashboard/app.js
```

- [x] Python 3.13.7 is used, not 3.12 compatibility evidence.
- [x] Every application command exits zero; exact versions and counts are
  recorded in the G1.6 handoff.
- [x] Import-isolation, secret and dangerous-code scans pass.
- [x] Only approved Codex-owned infrastructure/tests/docs/CI files differ from
  the G1.6 branch baseline.

## 5. SAM validation and target build

Track G1.6 used isolated SAM CLI 1.163.0: strict transformed-template lint
passed, a native CPython 3.13.7 ARM64 build succeeded, and both handlers imported
from the fresh artifacts. Private run `29649766982` repeated strict validation,
native ARM64 Python 3.13 build, and both handler imports successfully.

Install/use an approved SAM CLI without changing global software unexpectedly,
then run from the repository root:

```bash
sam validate --template-file infra/template.yaml
sam build -t infra/template.yaml
python infra/scripts/verify_built_handlers.py \
  .aws-sam/build/ProofLoopApiFunction proofloop.infrastructure.lambda_handler:handler \
  .aws-sam/build/ProofLoopScheduledFunction proofloop.infrastructure.scheduled_handler:scheduled_handler
```

- [x] Offline `sam validate --lint` succeeds with the approved region
  configuration and
  makes no AWS call.
- [x] Native local ARM64 build targets Python 3.13 and installs runtime
  dependencies only. A container build is optional evidence; native Linux
  target-architecture CI passed.
- [x] Both handlers and imported ProofLoop modules resolve from their build
  artifacts, not the editable source tree.
- [x] Built artifacts contain no `.env`, API key, credentials, raw invoice,
  test cache or development toolchain.
- [ ] Before G2 change-set creation, use a SAM release that permits fixed Click
  8.3.3+ or explicitly review and accept the isolated SAM 1.163.0
  `PYSEC-2026-2132` tooling advisory. The project/Lambda dependency audit is
  green; this is a local CLI dependency finding.
- [ ] The reviewed change set from `sam deploy --no-execute-changeset` or an
  equivalent preview contains only expected resources and IAM permissions.

## 6. Budget and monitoring before deploy

- [ ] AWS Budget exists with the approved monthly amount and alert thresholds.
- [ ] Cost Anomaly Detection or equivalent alerting is routed to the owner.
- [x] The final reviewed template defines the essential controlled-development
  alarms for API Lambda errors/throttles, scheduled Lambda errors/throttles,
  both SQS DLQ visible-message depths, EventBridge failed invocations, HTTP API
  5xx, and DynamoDB read/write throttling.
- [x] Product-owner-approved thresholds, evaluation periods, and missing-data
  behavior are implemented: one event/message in five minutes and missing data
  non-breaching. The stack-managed topic and parameterized email contain no
  invented destination; deploy-time address supply and confirmation remain open.
- [ ] Alert notifications are tested through an approved synthetic signal.
- [ ] Dashboard and runbook links are attached to each alarm.
- [ ] Log fields are reviewed to exclude keys, bodies, evidence payloads, scope
  identifiers and exception text beyond the customer-safe schema.

Production-scale extensions—duration/latency, concurrency headroom, API 4xx
rate, capacity trends, DLQ age, anomaly/composite alarms, privacy log filters,
SLO dashboards, and load-derived thresholds—may defer beyond the controlled
development deployment. They are not substitutes for the essential set.

## 7. Guarded deployment

**No executable deployment command is approved here.** The template now
contains `AllowedOrigin`, `EnableReconciliationSchedule`, and
`AlarmNotificationEmail` plus the approved alarms/topic/table policies. Track
G2 may create one non-executed change set only after the G1.6 private CI gate is
green and G2 is separately authorized. Only a later
execution authorization may publish the exact reviewed deploy command.

Create/export future parameter values through the approved secure process. The
API key must not be typed into a committed file or captured transcript. The
eventual command must include the approved API key, Bedrock model/profile and
ARN, Bedrock region, exact allowed origin, schedule disabled value, and approved
alarm email parameter.

- [ ] Human approver reviews the final CloudFormation change set.
- [ ] The change set shows the exact approved `AllowedOrigin` value and API
  Lambda environment injection.
- [ ] The change set shows the reconciliation schedule disabled for the first
  deployment.
- [ ] The change set shows only the approved essential alarms and notification
  actions; no invented destination or unexpected monitoring resource appears.
- [ ] Stack reaches `CREATE_COMPLETE`/`UPDATE_COMPLETE` without rollback.
- [ ] Outputs and physical resource IDs are captured without secrets.
- [ ] DynamoDB is on demand, encrypted and TTL-enabled with
  `AgentRegistryIndex`.
- [ ] API Lambda has only table operations, its named log group, and one
  `bedrock:InvokeModel` resource.
- [ ] Scheduled Lambda has no Bedrock permission and only index `Query`, not
  table `Scan`.
- [ ] Two distinct SQS failure queues and bounded retry/event-age policies exist.
- [ ] EventBridge rule exists but remains disabled throughout initial smoke.
- [ ] No hosted dashboard resource or unexpected public artifact is present.
- [ ] DynamoDB deletion and replacement behavior matches the approved data
  policy and rollback plan.
- [ ] Log groups have the approved retention and no unexpected payload data.

## 8. Post-deploy smoke sequence

Use only reserved synthetic data. Capture status/correlation/evidence references,
never request bodies, prompts, model output or secrets.

1. [ ] `GET /healthz` returns healthy.
2. [ ] Missing API key returns 401; wrong key returns 403.
3. [ ] Invalid and oversized requests return stable safe 400 errors.
4. [ ] Run the fake-model-equivalent deterministic application checks against
   the deployed read model where the deployment supports them.
5. [ ] Confirm the independent model-free canary and expected GREEN/AMBER/RED
   derivation without enabling the schedule.
6. [ ] Inspect DynamoDB and logs for metadata-only persistence and safe logs.
7. [ ] Verify both DLQ paths, both queue-depth alarms, and the controlled
   inspection/replay procedure using an approved synthetic failure.
8. [ ] Verify Lambda, EventBridge, HTTP API 5xx, and DynamoDB throttle alarm
   definitions, states, actions, and owner delivery without creating a real
   customer failure.
9. [ ] Exercise containment and rollback: API-key revocation/rotation procedure,
   schedule-disabled state, prior-artifact reference, data-retention behavior,
   and named rollback authority.
10. [ ] Confirm every prerequisite owner signs off before recurring work begins.
11. [ ] Through a separately reviewed CloudFormation stack update, enable the
    five-minute schedule; do not toggle it manually in the console.
12. [ ] Confirm scheduled reconciliation, the independent canary, bounded
    retries, and clean DLQ/alarm state.
13. [ ] Serve the existing dashboard locally, verify the exact allowed origin,
    and render compliance/timeline/incidents from the deployed boundary. Do not
    add hosted dashboard resources during this smoke.
14. [ ] With separate explicit authorization, run the guarded real-provider
    smoke:

```bash
PROOFLOOP_ALLOW_REAL_MODEL_SMOKE=true \
PROOFLOOP_MODEL_PROVIDER=bedrock \
python scripts/smoke_bedrock_invoice.py
```

15. [ ] Confirm the real-provider smoke, if authorized, prints only workflow/
    compliance status and token counts and cannot exceed the approved model-
    call, retry, timeout, and 2,000-output-token caps.

Do not report a real-model accuracy rate from this single smoke. It is
connectivity/contract evidence only.

## 9. Rollback triggers

Rollback immediately when any of these occurs:

- secret, invoice content, raw/redacted PII, prompt/model output or tool payload
  appears in a response, DynamoDB item, log, metric dimension or screenshot;
- wrong tenant/environment/boundary evidence affects another scope;
- missing/conflicting evidence can yield GREEN;
- canary FAIL does not drive RED, remediation alone yields GREEN, or fresh proof
  cannot recover;
- API authentication/CORS/size caps fail closed incorrectly;
- invocation exceeds the approved call/token/timeout caps;
- unexpected IAM permission, scan, fixed-cost resource, throttle storm, retry
  storm, or unowned DLQ message appears;
- material smoke or alarm check fails.

## 10. Rollback actions

Choose the least destructive safe action with the rollback owner.

1. [ ] Stop new input: restrict/disable the API route or rotate/revoke the API
   key through the approved channel.
2. [ ] Disable the reconciliation schedule if it is contributing to the fault.
3. [ ] Preserve customer-safe CloudFormation events, metrics and correlation
   references; never export raw sensitive payloads.
4. [ ] If the prior reviewed artifact/config is safe, deploy that exact version
   and re-run all smoke checks.
5. [ ] If containment requires removal, export only records required by the
   approved audit-retention policy, then obtain destructive-action approval.
6. [ ] Delete the explicit stack:

```bash
sam delete --stack-name "$PROOFLOOP_STACK_NAME" \
  --region "$PROOFLOOP_BEDROCK_REGION"
```

7. [ ] Verify the table, API, Lambdas, schedule, queues, log groups and build
   artifact bucket objects covered by the plan are removed; note CloudFormation
   or retention-policy exceptions.
8. [ ] Verify billing/alarms settle and no invocation remains.
9. [ ] Rotate the API key and any temporary deployment credentials.
10. [ ] Record cause, blast radius, evidence, owner and conditions for redeploy.

## 11. Completion record

- Deployed commit: `________________`
- Change-set ID: `________________`
- Stack/region: `________________`
- Smoke evidence: `________________`
- Alarm evidence: `________________`
- Security reviewer: `________________`
- Release approver: `________________`
- Rollback drill/evidence: `________________`
- Final status and UTC timestamp: `________________`
