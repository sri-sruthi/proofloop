# ProofLoop Track C — Final Agent/Application Integration Handoff

**Owner:** Codex, domain/application/infrastructure integration owner  
**Date:** 2026-07-18  
**Status:** `READY_FOR_DEPLOY` for an explicitly authorized first non-production deployment; not deployed and not production-ready

## Task

Integrate Claude's corrected invoice-agent workflow with ProofLoop's frozen
domain/application spine while preserving ownership and isolation. Run the real
workflow locally with a fake provider, translate every control observation into
exactly one requirement-bound evidence event, synchronize deterministic
compliance, expose an authenticated run endpoint, package an injected Bedrock
path with scoped IAM, add an adversarial demo/tests, consolidate documentation,
and stop before Git or AWS mutation.

## Customer outcome

A reviewer can now submit a bounded invoice transiently and watch the actual
agent controls earn assurance:

```text
PII redaction before model
  -> strict structured extraction
  -> deterministic reconciliation/policy
  -> HITL for unsafe/uncertain dispositions
  -> four exact runtime evidence events
  + one independent synthetic schema canary
  -> deterministic ProofLoop compliance/timeline/incidents
```

The response contains only bounded workflow status, token counts, safe tool
names/outcomes, evidence receipts, a controlled safe action, and compliance. It
never returns invoice/redacted text, prompts, model output, tool payloads,
observation reasons, PII findings/counts, failure text, chain-of-thought, or
human-review ticket details.

## Inputs read end to end

- Track C urgent brief and the product owner's approved-design follow-up.
- `docs/PROJECT_RULES.md` and the living handbook.
- `claude/handovers/ONE_DAY_AGENT_DELIVERY.md`.
- `claude/handovers/FINAL_AGENT_AND_SUBMISSION_NARRATIVE.md`.
- `claude/reviews/FINAL_AGENT_DOMAIN_COMPATIBILITY_REVIEW.md`.
- `codex/handovers/ONE_DAY_APPLICATION_SPINE.md`.
- Corrected agent source and privacy/Bedrock tests.
- Current domain, application, API, infrastructure, SAM, dashboard, demo and
  relevant tests.

## Ownership respected

No file under `src/proofloop/agents/**`, `tests/agents/**`, or `claude/**` was
modified. `proofloop.domain` and `proofloop.application` still import no agent
implementation. The API owns neutral run contracts and receives an
`InvoiceRunPort`; only `proofloop.infrastructure.agent_integration` imports both
agent and assurance contracts.

## Files created

- `src/proofloop/api/invoice_runs.py`
- `src/proofloop/infrastructure/agent_integration.py`
- `scripts/demo_agent_to_compliance.py`
- `scripts/smoke_bedrock_invoice.py`
- `tests/api/test_invoice_runs.py`
- `tests/integration/test_agent_evidence_bridge.py`
- `tests/integration/test_agent_workflow_integration.py`
- `tests/integration/test_agent_composition.py`
- `tests/integration/test_agent_privacy_boundary.py`
- `tests/integration/test_agent_integration_demo.py`
- `tests/integration/test_bedrock_smoke_guard.py`
- `docs/superpowers/specs/2026-07-18-proofloop-agent-application-integration-design.md`
- `docs/superpowers/plans/2026-07-18-proofloop-agent-application-integration.md`
- `codex/handovers/FINAL_AGENT_APPLICATION_INTEGRATION.md`

## Files updated

- `src/proofloop/api/app.py`
- `src/proofloop/application/errors.py`
- `src/proofloop/infrastructure/composition.py`
- `src/proofloop/infrastructure/scheduled_handler.py`
- `tests/integration/test_infra_contract.py`
- `infra/template.yaml`
- `infra/scripts/validate_template.py`
- `infra/README.md`
- `.env.example`
- `README.md`
- `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`

## Contract and behavior changes

### Neutral run boundary

`POST /v1/agents/{agent_id}/runs/invoice` is authenticated, uses the existing
256 KB adapter cap and a 100,000-character content cap, requires an opaque
non-numeric document reference, converts the request transiently, runs
`run_invoice_workflow`, emits available evidence, syncs, and returns
`InvoiceRunResponse`. OpenAPI includes complete request/response schemas.

Local WSGI and Lambda use the same `build_application` composition path.
Missing runner composition returns stable 503
`INTEGRATION_NOT_CONFIGURED`; agent/model/tool errors do not echo input or
exception text.

### Exact integrated definition

| Control | Requirement | Type/source |
|---|---|---|
| `invoice-pii-redaction` | `invoice-pii-redaction-runtime` | `CONTROL_EXECUTION` / `proofloop.agents.guardrails` |
| `invoice-audit-logging` | `invoice-audit-logging-runtime` | `AUDIT_EVENT` / `proofloop.agents.guardrails` |
| `invoice-hitl-boundary` | `invoice-hitl-boundary-runtime` | `CONTROL_OUTCOME` / `proofloop.agents.guardrails` |
| `invoice-extraction-guardrail` | `invoice-extraction-schema-runtime` | `CONTROL_OUTCOME` / `proofloop.agents.guardrails` |
| `invoice-extraction-guardrail` | `invoice-extraction-safe-canary` | `CANARY_RESULT` / `proofloop.safe_canary` |

One observation maps to one envelope and one requirement. Schema runtime proof
is never relabeled as a canary. `PASS/FAIL/UNAVAILABLE` map exactly. Raw UTC and
the exact tenant/environment/assurance-boundary/workflow/execution/trace are
preserved. SHA-256-derived bounded references are deterministic and distinct by
control/time/run identity; outcomes are excluded from logical identity so
contradictory reuse becomes a conflict.

Runtime evidence uses a complete applicable provenance vector: component,
prompt, provider/model, policy, schema, tool catalog, MCP (`None`),
orchestration, guardrail and runtime config. The integrated definition and
emitter share immutable `AgentIntegrationSettings`, so ingestion rejects drift.

### Independent safe canary

The canary uses a deliberately inconsistent synthetic `ExtractedInvoice` and
passes only when strict validation rejects it. It invokes no provider or
business tool, has a separate source/requirement/provenance vector, and carries
`synthetic=true`, `side_effects_absent=true`, and `canary_safe=true`.

### Privacy decisions

Original observation attributes are never forwarded. The only runtime evidence
booleans are `redaction_applied`, `audit_recorded`, `control_active`, and
`schema_valid`. The cross-layer regression poisons the invoice with an email,
phone, account number and prompt injection, then inspects:

- the provider request (placeholders; injection remains untrusted data);
- each mapped envelope;
- the in-memory evidence repository;
- invoice-run API and Lambda serialization;
- dashboard-bound compliance/timeline/incident payloads;
- captured Lambda logs.

Raw values, injection text, observation PII counts/keys and prohibited free text
are absent from every persisted/returned/logged surface.

### Failure semantics

- Malformed model output: extraction/schema observation FAIL → RED; no tool run.
- Model timeout/retry: hard `max_model_calls` cap remains authoritative and
  usage is bounded in the response.
- Reconciliation tool timeout: available evidence is retained; absent HITL proof
  remains AMBER rather than fabricated PASS/FAIL.
- Human-review timeout: the outer bridge converts the typed tool error into an
  unavailable HITL observation, keeps the invoice blocked, and returns AMBER
  without losing the PII/schema/audit observations already produced.
- Confirmed duplicate: deterministic BLOCK, idempotent human-review tool, HITL
  PASS, no payment tool.
- Exact replay: four runtime receipts become `DUPLICATE`; no new stored events.
- Contradictory replay: safe conflict/quarantine is synchronized to AMBER before
  the stable conflict error returns; no retry loop.
- Independent canary FAIL: RED.
- Repair declaration only: AMBER.
- Fresh runtime plus fresh synthetic canary PASS strictly after remediation:
  GREEN.

## Bedrock and SAM boundary

- `boto3` is imported only inside infrastructure composition.
- Local default is `FakeModelProvider`.
- Bedrock mode creates a fresh `BedrockConverseProvider` per invoice run while
  sharing only the region-selected runtime client and immutable configuration;
  its diagnostic request body therefore cannot linger in the warm application.
- SAM requires `BedrockModelId`, `BedrockModelArn`, and `BedrockRegion`; model
  call/retry/output-token/timeout limits are parameterized.
- API IAM has exactly one `bedrock:InvokeModel` action and uses
  `Resource: !Ref BedrockModelArn`; the scheduled function has no Bedrock action.
- The scheduled function refreshes the independent, model-free schema canary
  before each five-minute sync. Bedrock SDK retries are disabled
  (`total_max_attempts=1`), and configured connect/read timeouts prevent hidden
  client attempts from bypassing the agent's visible call cap.
- No credential or concrete model identifier is committed.
- The real smoke command refuses to run unless
  `PROOFLOOP_ALLOW_REAL_MODEL_SMOKE=true` and required settings are present. It
  exits successfully only after at least one model call, a completed workflow,
  emitted evidence, and GREEN compliance—not merely an HTTP 200 response.
- No AgentCore, Strands, Cognito, React, OpenSearch, NAT, ECS, EKS, or always-on
  compute was added.

## TDD evidence

Focused tests were observed RED before implementation:

- missing neutral API and bridge modules failed collection;
- missing `InvoiceAgentRunner` and `build_invoice_runner` failed collection;
- absent Bedrock SAM parameters/IAM failed the structural test;
- absent smoke/demo commands failed their subprocess tests.

Each focused slice was made GREEN before moving to the next one. The completed
named coverage includes mapping, provenance, privacy/prompt injection,
idempotency/conflict, malformed/model/tool failures, HITL, call/token caps,
agent-to-GREEN, canary RED, remediation recovery, Bedrock stub composition,
API/Lambda parity, import isolation, SAM scoping and both demos.

## Fresh verification results

Executed on Python 3.12.7 and Node 22.18.0:

```text
python -m pytest -q
  -> 263 passed in 1.30s
python -m mypy src/proofloop tests
  -> Success: no issues found in 88 source files
python -m compileall -q src tests scripts infra/scripts
  -> exit 0
python scripts/demo_proofloop.py
  -> GREEN -> AMBER -> RED -> AMBER -> GREEN; resolved incident has 4 refs
python scripts/demo_agent_to_compliance.py
  -> GREEN -> AMBER -> GREEN -> RED -> AMBER -> GREEN;
     malformed output RED; tool failure AMBER; no payment tool
python infra/scripts/validate_template.py
  -> SAM package guardrails passed
source-tree HTTP + scheduled Lambda imports
  -> handler scheduled_handler; exit 0
node --check dashboard/app.js
  -> exit 0
Lambda makefile dry-runs for both functions
  -> exit 0
domain/application agent-import scan
  -> no matches
domain/application/API AWS-SDK import scan
  -> no matches
dangerous execution/deserialization source scan
  -> no matches
```

`sam`, Ruff, Bandit, pip-audit, Python 3.13 and `uv` are unavailable locally,
so no local result is claimed. The CI matrix defines the applicable clean-runner
checks but has not run because no Git mutation/push was authorized. `python -m
pip check` reports unrelated pre-existing conflicts in the shared Anaconda
environment (TensorFlow/NumPy, Streamlit/Pillow, and others); it is not
represented as a passing ProofLoop dependency audit.

## Production risks and limitations

- No AWS deployment, real Bedrock request, accuracy evaluation, latency
  measurement or real-cost evidence exists.
- The regex redactor covers a bounded demonstration set and is not complete DLP.
- Fake/stub fixtures are not a dataset and model confidence is uncalibrated.
- Business tools are in-memory demonstrations; there is no MCP runtime or live
  AP/ERP integration.
- API-key auth is not production identity/authorization/rotation/quotas/WAF.
- DynamoDB/SAM behavior remains contract/structural-tested, not live-table or
  live-Lambda tested under throttling/concurrency.
- Conflict quarantine has no operator resolution use case and remains AMBER
  while conflicting records are retained.
- Idempotency is implemented for exact evidence-event re-emission and the
  human-review write. The invoice endpoint does not yet accept a caller run key,
  so a later re-execution is a new observation rather than a command retry.
- Production still needs alarms, rollback, DLQ ownership/replay, quotas,
  retention decisions, load/fault tests, observability ownership and cost budget.
- The model ARN/region must be chosen for a compatible foundation model or
  inference profile and reviewed for required underlying permissions/pricing.

## Deployment prerequisites requiring human authority

Before a first non-production deployment, the product owner must explicitly
authorize deployment and supply/approve:

1. AWS account, region and stack name.
2. Secure API-key delivery/rotation method.
3. Bedrock model/inference-profile ID and exact least-privilege ARN.
4. Model call/retry/timeout limits and a spend budget/alarm.
5. Allowed browser origin and non-production tenant/boundary identity.
6. CI/SAM validate+container build results, rollback/delete plan and log/DLQ
   ownership.

No Git add/commit/branch/push/PR and no AWS command/resource/model invocation was
performed.

## Final disposition

`READY_FOR_DEPLOY`

This means the requested local/stubbed Track C slice passes its available gate
and is ready for a separately authorized first non-production deployment. It is
not a production-readiness or real-model-success claim.
