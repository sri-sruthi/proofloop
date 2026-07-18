# ProofLoop Post-Activation Deployment and Rollback Checklist

**Status:** planned, exact, and deliberately **not executed** through Track E2.  
**Account fact:** payment verification is complete and Lambda is accessible in
`ap-south-1`, as stated by the product owner; Track E2 made no AWS call.  
**Trigger:** the product owner separately authorizes the exact cloud resources,
change set and bounded real-model smoke after the remaining gates pass.  
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
- [ ] **Browser origin:** exact HTTPS dashboard origin for CORS:
  `________________`.
- [ ] **Tenant ID:** `________________`.
- [ ] **Environment:** `DEVELOPMENT`, `STAGING`, or approved alternative:
  `________________`.
- [ ] **Assurance-boundary ID:** `________________`.
- [ ] **Monthly budget and thresholds:** amount `________`; notification
  recipients `________________`; anomaly and hard-stop policy `________________`.
- [ ] **CloudWatch/log owner:** `________________`; 30-day retention accepted or
  changed through an approved template update.
- [ ] **EventBridge delivery DLQ owner:** `________________`.
- [ ] **Lambda on-failure DLQ owner:** `________________`.
- [ ] **DLQ inspection/replay runbook:** approved location `________________`.
- [ ] **Rollback authority:** `________________`; may disable schedule, roll back
  code/config, export required evidence, or delete the stack.
- [ ] **Private GitHub authorization:** owner/repository name, visibility,
  branch protections and allowed collaborators recorded; no repository creation
  before approval.
- [ ] **CI authorization:** secrets/OIDC approach, protected environments,
  required checks and deploy approvers recorded.

## 2. Local blockers and remaining predeployment prerequisites

- [x] RUFF-01: authorized owners removed the unused agent import and replaced
  the two assigned infrastructure lambdas with typed named functions; exact CI
  Ruff command exits zero.
- [x] BANDIT-01: both public assurance `PASS` literals retain their serialized
  contract and carry narrow, documented line-level B105 suppressions; the exact
  Bandit command exits zero without a global disable.
- [x] AUDIT-01: pytest 9 compatibility passed; the dev policy is
  `pytest>=9.0.3,<10`; strict audit reports no known vulnerabilities in the
  clean disposable environment after its bootstrap pip was upgraded.
- [x] Claude's independent audit was received and triaged; Track E2 did not
  implement optional O1/O2 or cross the agent ownership boundary.
- [ ] A baseline commit/private remote exists so the review diff is auditable.
- [ ] Python 3.13, SAM validation/container build, built-handler verification
  and protected CI complete with captured evidence.

## 3. Read-only account and model preflight

These commands contact AWS but do not create resources. Run only after account
explicit preflight authorization.

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

- [ ] Python 3.13 is used, not 3.12 compatibility evidence.
- [ ] Every command exits zero; exact versions and counts are attached.
- [ ] Import-isolation, secret and dangerous-code scans pass.
- [ ] Only approved files differ from the reviewed baseline.

## 5. SAM validation and target build

Install/use an approved SAM CLI without changing global software unexpectedly,
then run from the repository root:

```bash
sam validate --template-file infra/template.yaml
sam build -t infra/template.yaml --use-container
python infra/scripts/verify_built_handlers.py \
  .aws-sam/build/ProofLoopApiFunction proofloop.infrastructure.lambda_handler:handler \
  .aws-sam/build/ProofLoopScheduledFunction proofloop.infrastructure.scheduled_handler:scheduled_handler
```

- [ ] `sam validate` succeeds against the target account/region.
- [ ] Container build targets ARM64 Python 3.13 and installs runtime dependencies
  only.
- [ ] Both handlers and imported ProofLoop modules resolve from their build
  artifacts, not the editable source tree.
- [ ] Built artifacts contain no `.env`, API key, credentials, raw invoice,
  test cache or development toolchain.
- [ ] The reviewed change set from `sam deploy --no-execute-changeset` or an
  equivalent preview contains only expected resources and IAM permissions.

## 6. Budget and monitoring before deploy

- [ ] AWS Budget exists with the approved monthly amount and alert thresholds.
- [ ] Cost Anomaly Detection or equivalent alerting is routed to the owner.
- [ ] Alarms exist for API and scheduled Lambda errors, duration, throttles and
  concurrency; API 4xx/5xx; DynamoDB throttles/capacity; both SQS DLQ depths; and
  EventBridge failed invocations.
- [ ] Alert notifications are tested through an approved synthetic signal.
- [ ] Dashboard and runbook links are attached to each alarm.
- [ ] Log fields are reviewed to exclude keys, bodies, evidence payloads, scope
  identifiers and exception text beyond the customer-safe schema.

## 7. Guarded deployment

Create/export parameter values through the approved secure process. The API key
must not be typed into a committed file or captured transcript.

```bash
sam deploy --guided --template-file .aws-sam/build/template.yaml \
  --stack-name "$PROOFLOOP_STACK_NAME" \
  --region "$PROOFLOOP_BEDROCK_REGION" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    "ApiKey=$PROOFLOOP_API_KEY" \
    "BedrockModelId=$PROOFLOOP_BEDROCK_MODEL_ID" \
    "BedrockModelArn=$PROOFLOOP_BEDROCK_MODEL_ARN" \
    "BedrockRegion=$PROOFLOOP_BEDROCK_REGION"
```

- [ ] Human approver reviews the final CloudFormation change set.
- [ ] Stack reaches `CREATE_COMPLETE`/`UPDATE_COMPLETE` without rollback.
- [ ] Outputs and physical resource IDs are captured without secrets.
- [ ] DynamoDB is on demand, encrypted and TTL-enabled with
  `AgentRegistryIndex`.
- [ ] API Lambda has only table operations, its named log group, and one
  `bedrock:InvokeModel` resource.
- [ ] Scheduled Lambda has no Bedrock permission and only index `Query`, not
  table `Scan`.
- [ ] Two distinct SQS failure queues and bounded retry/event-age policies exist.
- [ ] EventBridge runs every five minutes; leave it disabled until smoke
  ownership is ready if the approved rollout plan requires that.
- [ ] Log groups have the approved retention and no unexpected payload data.

## 8. Post-deploy smoke sequence

Use only reserved synthetic data. Capture status/correlation/evidence references,
never request bodies, prompts, model output or secrets.

1. [ ] `GET /healthz` returns healthy.
2. [ ] Missing API key returns 401; wrong key returns 403.
3. [ ] Invalid and oversized requests return stable safe 400 errors.
4. [ ] Run the fake-model-equivalent deterministic application checks against
   the deployed read model where the deployment supports them.
5. [ ] With separate explicit authorization, run the guarded real-provider smoke:

```bash
PROOFLOOP_ALLOW_REAL_MODEL_SMOKE=true \
PROOFLOOP_MODEL_PROVIDER=bedrock \
python scripts/smoke_bedrock_invoice.py
```

6. [ ] Confirm the smoke prints only workflow/compliance status and token counts.
7. [ ] Confirm one bounded invoice run cannot exceed the approved model-call,
   retry, timeout and 2,000-output-token caps.
8. [ ] Confirm five-minute reconciliation and the independent model-free canary.
9. [ ] Confirm compliance, timeline and incident API/dashboard rendering from
   the deployed boundary and approved browser origin.
10. [ ] Inspect DynamoDB and logs for metadata-only persistence and safe logs.
11. [ ] Exercise an approved synthetic failure through RED, remediation AMBER,
   and fresh-proof GREEN without touching a customer workflow.
12. [ ] Verify both DLQ alarm paths and the controlled replay procedure.

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
