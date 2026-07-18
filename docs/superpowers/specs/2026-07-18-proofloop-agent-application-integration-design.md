# ProofLoop Track C Agent-to-Assurance Integration Design

**Date:** 2026-07-18  
**Status:** Reviewed and approved by the product owner  
**Scope:** Local-to-AWS integration only; no commit, push, deployment, credential use, paid invocation, or cloud-resource creation

## Outcome

Track C connects the corrected invoice agent workflow to ProofLoop's deterministic
assurance application without coupling the agent package to domain contracts. An
authenticated invoice-run request is processed transiently, each agent control
observation becomes exactly one requirement-bound evidence event, assurance is
synchronized, and the caller receives a bounded PII-free summary.

## Architecture

The dependency direction remains inward:

```text
domain <- application <- API-neutral run contract
                 ^
                 |
infrastructure agent bridge -> proofloop.agents
```

- `proofloop.domain` and `proofloop.application` never import `proofloop.agents`.
- `proofloop.api` owns only validated request/response models and an injected
  invoice-run protocol. It does not construct providers or import agent code.
- `proofloop.infrastructure` owns the bridge, provider/tool composition, boto3
  construction, and the mapping between agent observations and assurance evidence.
- Local WSGI and Lambda use the same `build_application` composition path.

## Integrated agent definition

The registered invoice-agent definition contains four controls. Runtime and
synthetic obligations are separate requirements:

| Control | Requirement | Evidence type | Source |
|---|---|---|---|
| PII redaction | `invoice-pii-redaction-runtime` | `CONTROL_EXECUTION` | `proofloop.agents.guardrails` |
| Audit logging | `invoice-audit-logging-runtime` | `AUDIT_EVENT` | `proofloop.agents.guardrails` |
| HITL boundary | `invoice-hitl-boundary-runtime` | `CONTROL_OUTCOME` | `proofloop.agents.guardrails` |
| Extraction guardrail | `invoice-extraction-schema-runtime` | `CONTROL_OUTCOME` | `proofloop.agents.guardrails` |
| Extraction guardrail | `invoice-extraction-safe-canary` | `CANARY_RESULT` | `proofloop.safe_canary` |

Schema-validation observations are never relabeled as canaries. The safe canary
is independently emitted with `synthetic=true` and
`side_effects_absent=true`. The extraction control therefore requires both fresh
runtime proof and independently attested canary proof before it can be GREEN.

## Observation-to-evidence mapping

Each `ControlObservation` maps to one and only one declared requirement:

| `ControlKey` | Control / requirement | Safe boolean metadata |
|---|---|---|
| `PII_REDACTION` | PII / runtime | `redaction_applied` |
| `AUDIT_LOGGING` | audit / runtime | `audit_recorded` |
| `HITL_BOUNDARY` | HITL / runtime | `control_active` |
| `EXTRACTION_SCHEMA_VALIDATION` | extraction / runtime | `schema_valid` |

The bridge maps outcomes exactly: `PASS -> PASS`, `FAIL -> FAIL`, and
`UNAVAILABLE -> UNAVAILABLE`. It preserves the observation's raw UTC timestamp
and stamps the exact registered tenant, environment, assurance boundary,
workflow, execution, and trace identity.

`source_event_id` is a bounded deterministic SHA-256-derived reference over the
logical run identity, opaque document reference, control key, and raw observation
timestamp. It deliberately excludes the outcome and attributes: exact replay is
idempotent, while contradictory reuse of the same logical identity is quarantined
as a conflict. `evidence_id` is a separate deterministic bounded reference.

Every runtime requirement has an exact ten-field provenance vector. Composition
supplies mandatory component, policy, schema, orchestration, and runtime-config
versions; the workflow result supplies the prompt/provider versions; composition
supplies the tool-catalog label; MCP remains `None`; the observation supplies the
guardrail version. The definition and emitted evidence are built from the same
integration configuration so exact comparison is intentional and testable.

## Privacy boundary

Raw and redacted invoice text exist only in the transient request/agent call.
The bridge never persists or returns invoice text, prompts, model output, tool
payloads, observation reasons, safe-action strings from observations, PII
findings, or PII counts. It emits only bounded opaque identifiers, enums,
timestamps, exact provenance labels, and the approved booleans listed above.

The run response contains only workflow status/stage/disposition, bounded model
call and token counts, tool names with enum outcomes, evidence references and
ingestion statuses, a controlled safe-action code/text selected by the bridge,
and the current compliance read model. It exposes neither chain-of-thought nor
raw provider output. Logs remain limited to route/status/request metadata.

## Endpoint and failure behavior

`POST /v1/agents/{agent_id}/runs/invoice` uses the existing API-key boundary and
body cap, plus bounded Pydantic fields. Tenant/environment/assurance-boundary are
validated exactly like existing routes. The request's `document_id` is an opaque
reference; invoice content is transient.

The bridge returns typed workflow failures rather than exposing exception text.
Observations produced before a model/tool failure are still emitted. Missing
required later observations remain AMBER unless an explicit current FAIL makes
the aggregate RED. Evidence conflicts use the existing safe 409/quarantine
semantics. No retry loop is created for a conflict.

## Provider, tools, and AWS composition

Local mode uses a deterministic `FakeModelProvider`. Bedrock mode constructs a
`boto3.client("bedrock-runtime")` only in infrastructure and injects it into
`BedrockConverseProvider`. Model ID, scoped model ARN, region, provider label,
model-call cap, retry cap, token cap, and timeout come from environment/SAM
parameters. No credential or model identifier is committed.

SAM grants only `bedrock:InvokeModel` on the required model ARN parameter. It
adds no AgentCore, Strands, Cognito, React, OpenSearch, NAT, ECS, or EKS resource.
A real-provider smoke script is present but refuses to run without an explicit
guard environment flag. It will not be executed during Track C.

The business tools remain deterministic in-memory demonstration adapters. They
include purchase-order, vendor, duplicate, and human-review operations; there is
no payment tool.

## Verification and demonstration

Tests cover exact mapping, provenance, cross-layer privacy, prompt injection,
idempotency/conflict, model/tool failure, HITL, limits, GREEN, safe-canary RED,
post-remediation recovery, API/Lambda parity, Bedrock stub composition, import
isolation, and SAM scoping.

`scripts/demo_agent_to_compliance.py` shows poisoned input, redaction before the
model, extraction, deterministic reconciliation, HITL, evidence, compliance,
duplicate/malformed/failure paths, replay/conflict, safe-canary RED, remediation
AMBER, fresh-evidence GREEN, bounded usage, and the absence of a payment tool.

Completion is `READY_FOR_DEPLOY` only after the full local verification gate
passes. Deployment still requires a separate explicit authorization.
