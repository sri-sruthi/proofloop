# ProofLoop AWS SAM slice

This package deploys only pay-per-use infrastructure: an ARM64 Python 3.13 HTTP
Lambda, a separate five-minute reconciliation Lambda, one HTTP API, one DynamoDB
on-demand table, EventBridge scheduling disabled by default, two SQS failure
queues, 30-day CloudWatch log groups, ten standard metric alarms, and one
stack-managed SNS topic with an email subscription. It does **not** provision a
hosted dashboard, NAT Gateway, OpenSearch, EKS, ECS, databases with fixed
capacity, or any other always-on compute.

## Data and access boundaries

The application owns the DynamoDB item convention. Every item must use a
tenant-and-assurance-boundary partition key:

```text
PK = TENANT#{tenant_id}#ENV#{environment}#BOUNDARY#{assurance_boundary_id}
SK = AGENT#{agent_id}#DEFINITION
   | AGENT#{agent_id}#COMPLIANCE
   | AGENT#{agent_id}#EVIDENCE#{sha256(workflow + execution + trace + source + source_event)}
   | AGENT#{agent_id}#EVIDENCE-ID#{sha256(evidence_id)}
   | AGENT#{agent_id}#EVIDENCE#{identity_hash}#CONFLICT#{payload_hash}
   | AGENT#{agent_id}#STATE-REVISION
   | AGENT#{agent_id}#TIMELINE#{zero_padded_revision}#{transition_id}
   | AGENT#{agent_id}#INCIDENT#{incident_id}

Agent-definition registry keys only:
GSI1PK = AGENT_REGISTRY
GSI1SK = TENANT#{tenant_id}#ENV#{environment}#BOUNDARY#{assurance_boundary_id}#AGENT#{agent_id}
```

The evidence identity hash joins workflow ID, execution ID, trace ID, source,
and source-event ID with ASCII unit separators before SHA-256. Agent definitions
and state-revision records have no TTL. Evidence, evidence-ID, conflict, and
compliance records expire after eight days; timeline entries use their
application-defined seven-day expiry; incidents expire 30 days after opening or,
for resolved incidents, 30 days after resolution. The state revision is advanced
in the same transaction as compliance/timeline/incident state and is the timeline
sort sequence, so equal timestamps retain commit order. `ttl` is the Unix epoch
second at which an expiring item becomes eligible for DynamoDB's asynchronous
deletion. These are implementation retention controls, not proof that deletion
happens at the exact TTL instant.

The base partition key preserves tenant-local queries. `AgentRegistryIndex`
projects agent-definition records so the five-minute reconciler discovers active
scopes with a paginated `Query` on `GSI1PK = AGENT_REGISTRY`; it no longer scans
the full table. The GSI is eventually consistent, so a newly registered agent
can miss one reconciliation interval before appearing. The table and index use
on-demand billing, and the scheduled role has no `dynamodb:Scan` permission.
Only that role receives `dynamodb:Query` on the
`AgentRegistryIndex` ARN; the API role remains table-only.

The remaining volume risk is per agent: evaluation queries that agent's retained
evidence prefix and filters the requested workflow in application code. A high
event-rate agent can therefore accumulate substantial evidence, evidence-ID,
and conflict items during the eight-day retention window, increasing read cost,
pagination, memory, and reconciliation time even though global discovery is
bounded. Before high-volume production use, add a workflow/time-oriented access
path or compaction policy, set measured per-agent ingestion limits, shard the
schedule, and alarm on query pages, consumed capacity, duration, throttles, and
DLQ depth.

The table has no raw invoice payload or PII fields; only validated evidence
metadata and customer-safe references belong there. Lambda roles permit the
table operations needed for tenant-keyed reads and append/update flows,
including table-scoped `TransactWriteItems` for atomic evidence/idempotency and
compliance/timeline/incident commits, plus only their named log groups.

The function has no delete permission. Lambda platform logs use JSON format,
and the handler emits only structured, customer-safe event names and status
values—never API keys, raw evidence payloads, scope identifiers, or exception
text.

## Failure retries and dead-letter queues

There are two asynchronous failure planes, each bounded to a five-minute event
age and two retries:

- EventBridge rule delivery failures use the schedule `RetryPolicy`, then the
  SAM-managed `ProofLoopScheduledDeadLetterQueue` and its generated,
  rule-scoped SQS resource policy.
- Handler exceptions occur after Lambda accepted the EventBridge invocation, so
  Lambda—not EventBridge—performs those retries. `EventInvokeConfig` sends an
  exhausted event to a separate SAM-managed SQS on-failure destination and adds
  only the required `sqs:SendMessage` permission to the generated Lambda role.

Both queues are standard, request-priced SQS resources with no always-on
consumer. The template intentionally does not auto-redrive them: an operator
must inspect customer-safe failure metadata, correct the cause, and explicitly
replay. The development template now alarms on both queue depths, but execution
still needs a confirmed notification subscription, named owner/runbook, and a
verified replay procedure.

`ApiKey` is a `NoEcho` CloudFormation parameter injected as
`PROOFLOOP_API_KEY`. It has no default and must be supplied securely at deploy
time. Do not place its value in this repository, `samconfig.toml`, logs, or shell
history. This API-key check is a controlled development/demo boundary, not
customer-production identity, IAM authorization, or a substitute for key
rotation and per-principal access control.

`AllowedOrigin` is also required and has no default. It is injected as
`PROOFLOOP_ALLOWED_ORIGIN`; the parameter constraint permits one explicit
HTTP(S) origin and rejects `*`. The approved controlled-demo value is
`http://localhost:8000`. The SAM stack hosts no dashboard: deploy and smoke the
backend first, then serve the existing dashboard locally.

`AssuranceBoundaryId` is required and has no default. It is injected as
`PROOFLOOP_DEMO_BOUNDARY_ID` into both Lambda functions and identifies the exact
assurance boundary this deployment is authorized to certify. There is no
hard-coded boundary in the template, so a deployment can never silently certify
a different customer boundary; the constraint rejects wildcards and blank
values. The approved controlled-development value is
`proofloop-demo-dev-invoices`.

`EnableReconciliationSchedule` accepts only `true` or `false` and defaults to
`false`. Keep it false for the first deployment. Enabling it starts recurring
Lambda, DynamoDB, EventBridge, log, and possible failure-path operations, so it
requires a separately reviewed stack update after health, authentication,
persistence, canary, DLQ, alarm-notification, and rollback smoke checks pass.

## Development monitoring and cost boundary

The template defines ten essential standard-resolution alarms: API and
scheduled Lambda errors/throttles, both visible-message DLQ depths, EventBridge
failed invocations, HTTP API 5xx, and DynamoDB read/write throttles. Each uses a
300-second period, one evaluation period, threshold 1, and missing data as
non-breaching. Every alarm publishes to `ProofLoopAlarmTopic`; the required
`AlarmNotificationEmail` parameter creates an email subscription that the
product owner must confirm before execution. Do not treat an unconfirmed
subscription as operational coverage.

The Lambdas, HTTP API, on-demand table/GSI, EventBridge rule, SQS queues, SNS
requests/delivery, log ingestion/storage, and SAM artifact storage are usage-
priced. The ten alarms accrue alarm metric-hours while they exist even when the
schedule is disabled; account-wide free-tier availability must not be assumed.
There is no hosted-dashboard or always-on-compute charge. Bedrock is a separate
token-priced path and remains unauthorized until a later explicit smoke decision.

The evidence table uses `DeletionPolicy: Delete` and
`UpdateReplacePolicy: Retain`. Stack deletion therefore deletes the controlled
development table and its data; export any required evidence before teardown.
If an update replaces the table, CloudFormation retains the old table to reduce
accidental replacement loss, but the orphan continues to incur storage/usage
cost until a named owner reviews and deletes it.

## Invoice agent and Bedrock boundary

The HTTP Lambda composes the same injected invoice-run bridge used by the local
WSGI server. Locally, `PROOFLOOP_MODEL_PROVIDER=fake` uses the deterministic
offline provider. The packaged AWS path selects `bedrock` and requires deployment
parameters for `BedrockModelId`, `BedrockModelArn`, and `BedrockRegion`. The API
role receives exactly one `bedrock:InvokeModel` action on `BedrockModelArn`; the
scheduled reconciler receives no model permission.

`MaxModelCalls`, `MaxModelRetries`, `MaxOutputTokens`, and `ModelTimeoutSeconds`
bound each run and are injected as environment values. The default API Lambda
timeout is 45 seconds, while the model timeout parameter is capped at 40 seconds.
Boto3 is imported only inside the infrastructure composition root; the
agent/domain/application/API contracts remain SDK-free. No credentials or
concrete model identifier are stored in the repository.

Each invoice run receives a fresh Bedrock provider adapter while reusing only the
SDK client and immutable provider configuration. This keeps its diagnostic copy
of the redacted request body scoped to the transient run instead of the warm
Lambda application.

The extraction safe canary is separate from runtime schema evidence. It validates
that a deliberately inconsistent synthetic invoice is rejected by the strict
schema, invokes no model or business tool, and records `synthetic=true` plus
`side_effects_absent=true`. The five-minute scheduled reconciler refreshes this
independent canary before synchronization. SDK-level Bedrock retries are disabled
(`total_max_attempts=1`) so the agent's visible call/retry caps remain the only
retry authority; client connect/read timeouts use `ModelTimeoutSeconds`.

## Validate and build

Run these commands from the repository root. They do not create AWS resources.

```bash
python3 infra/scripts/validate_template.py
sam validate --lint --template-file infra/template.yaml
PYTHON="$(command -v python3.13)" sam build -t infra/template.yaml
python infra/scripts/verify_built_handlers.py \
  .aws-sam/build/ProofLoopApiFunction proofloop.infrastructure.lambda_handler:handler \
  .aws-sam/build/ProofLoopScheduledFunction proofloop.infrastructure.scheduled_handler:scheduled_handler
```

The native build must resolve `python3.13`; passing `PYTHON` prevents a host
Python 3.12 from producing an ABI-incompatible native wheel. Target Linux ARM64
evidence comes from the private native ARM64 Python 3.13 CI job; a container
build is optional local evidence and is not claimed here. A root `Makefile`
includes the custom `infra/lambda/Makefile`; the
repository-root build context makes `pyproject.toml` and `src/proofloop`
available after SAM isolates the source. The custom Makefile copies the package and installs
only `[project].dependencies`; it never installs the development toolchain. The
artifact verifier clears previously imported `proofloop` modules and confirms
each handler and all imported ProofLoop modules resolve inside the corresponding
SAM build directory, rather than accidentally passing via the editable source
installation.

## Deploy and remove

Deployment creates billable AWS resources and requires explicit authorization.
The following is a future parameter example, not authorization to deploy.
After separate authorization, place secret values in the approved ephemeral
channel, ensure the command is not captured in shell history, and use the
reviewed equivalents of:

```bash
sam deploy --guided --template-file .aws-sam/build/template.yaml \
  --stack-name proofloop-dev --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    "ApiKey=$PROOFLOOP_API_KEY" \
    "AllowedOrigin=http://localhost:8000" \
    "AssuranceBoundaryId=proofloop-demo-dev-invoices" \
    "EnableReconciliationSchedule=false" \
    "AlarmNotificationEmail=$PROOFLOOP_ALARM_EMAIL" \
    "BedrockModelId=$PROOFLOOP_BEDROCK_MODEL_ID" \
    "BedrockModelArn=$PROOFLOOP_BEDROCK_MODEL_ARN" \
    "BedrockRegion=$PROOFLOOP_BEDROCK_REGION"
```

The email value is supplied only at deployment and is never committed; the
product owner is the initial development responder and must confirm the SNS
subscription. The first guided deployment can also choose the S3 artifact
bucket. Confirm the schedule is disabled and inspect every prompted change
before accepting it. To remove the stack and stop most stack charges:

```bash
sam delete --stack-name proofloop-dev
```

Deletion removes the current evidence table, failure queues, alarms, topic, and
log groups, so export any records needed for audit retention before running it.
A table retained by an earlier replacement is not removed with the current
stack and needs a separately reviewed cleanup to stop its orphan cost.

## Guarded real-provider smoke

Track C does not run a real model. After a deployment/model invocation has been
separately authorized and AWS credentials are available through the normal SDK
chain, the opt-in smoke is:

```bash
PROOFLOOP_ALLOW_REAL_MODEL_SMOKE=true \
PROOFLOOP_MODEL_PROVIDER=bedrock \
python scripts/smoke_bedrock_invoice.py
```

The command refuses to run without the explicit guard and required model/region
configuration. It prints only status, token counts, and compliance state—not the
request, model output, or invoice content.
