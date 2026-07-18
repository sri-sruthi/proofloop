# DECISIONS — ProofLoop PS-6.2 design rationale (ADR log)

*Purpose: capture the reasoning and trade-offs behind every material choice so any
"why did you…?" has a defensible answer, and to seed the PDF's design-rationale
section. Canonical product is **PS-6.2: Runtime-to-Compliance Evidence Assurance**
(ProofLoop); `docs/PROJECT_RULES.md` is authoritative.*

**Format:** Decision / Options considered / Why this one / Trade-offs & limits
(be honest) / Customer impact (Aivar's fifth element).

> **Status note (2026-07-18).** ProofLoop's agent layer is now **integrated** with
> the domain/application spine via `proofloop.infrastructure.agent_integration`
> (Codex Track C). Verified locally: 263 tests pass, mypy clean (88 files). It is
> **not deployed**, has made **no real Bedrock request**, is **not production-ready**,
> and uses **no MCP runtime**.

---

## D0 — Problem statement: PS-6.2 ProofLoop (not PS-3.2 / PS-5.1 / research tracks)

**Decision:** Build PS-6.2, a runtime-to-compliance **evidence assurance** platform
that continuously proves whether a production AI agent's declared safety controls
are actually executing — reference workload: a two-agent invoice workflow.

**Options considered (and why rejected — kept, not deleted, in `claude/`):**
- **PS-3.2 Behavioral Injection Detector** (earlier seed of this file): a
  behavioral-anomaly ML detector. *Rejected:* its verdict is probabilistic and
  non-reproducible; a compliance/payment gate must be deterministic and auditable.
  The ML-detection strength is reframed here as *evidence*, never as the verdict.
- **PS-5.1 Agent WAF / "AegisFlow" / "Vigil" / "Sentinel":** inline policy
  enforcement / cross-session behavioral baselines. *Rejected as the product:*
  overlaps AWS's own deterministic guardrails and is a crowded space; ProofLoop
  instead answers the *unmet* question — "is the control still firing *now*, with
  fresh evidence tied to this exact execution?" — which dashboards do not.
- **Maximal AgentCore / multi-framework orchestration:** *Rejected:* scope risk
  and lock-in; PS-6.2's value is the deterministic evidence core, not an agent
  framework.

**Why this one:** it is the most defensible under ex-AWS scrutiny — a narrow, hard,
deterministic problem with a permanent honesty promise ("no unsupported green"),
cloud-neutral core, and a clear customer harm it prevents.

**Trade-offs:** narrower demo surface than a flashy detector; requires rigorous
contracts. **Customer impact:** operators stop trusting a green that no longer
reflects reality.

## D1 — Deterministic verdict; the LLM never decides

**Decision:** The final GREEN/AMBER/RED assurance state, and the invoice
**disposition**, are pure deterministic reductions over typed evidence. The LLM may
only read text into structured fields (and, later, polish prose).

**Options considered:** LLM-as-judge; hybrid ML score gating the verdict.
**Why:** identical inputs must yield identical, explainable outputs when the result
gates a payment or a customer-safety claim; LLM judges are non-reproducible and
biased. Probabilistic signals may *support* but never independently declare GREEN
(PROJECT_RULES invariant).
**Trade-offs:** the model can't "smooth over" ambiguity — ambiguity becomes AMBER.
**Customer impact:** no black-box score; every state has reason codes and evidence.

## D2 — Two agents (extraction + reconciliation), not one

**Decision:** Split extraction (model, untrusted document text → strict fields) from
reconciliation (deterministic, authoritative tool records → typed mismatches).
**Options considered:** one mega-agent; three+ agents.
**Why:** different trust models and failure modes. Splitting keeps the model's blast
radius to "read text → fields" and lets reconciliation/policy be provably
deterministic; merging would place untrusted text next to authoritative-fact logic.
A third agent was deliberately not added; the reconciliation prompt is authored but
reserved.
**Trade-offs:** an extra hop and contract. **Customer impact:** a manipulated
extraction cannot rewrite a PO total, because facts come only from tools.

## D3 — Requirement-bound evidence (one event → one requirement)

**Decision:** Every evidence event names exactly one `requirement_id`; each guardrail
observation maps to exactly one requirement-bound `EvidenceEnvelope`.
**Options considered:** one event satisfying multiple obligations (the original B1
defect). *Rejected:* one redaction event could then also "prove" human approval.
**Why:** obligations must be independently provable. **Trade-offs:** more events to
emit. **Customer impact:** a green release/payment can't be manufactured by
double-counting a single proof.

## D4 — Independent safe canary, separate from runtime schema evidence

**Decision:** A synthetic, model-free canary probes strict-schema rejection and
carries its own `requirement_id`, `CANARY_RESULT` type, source, and provenance;
runtime schema proof is never relabeled as a canary.
**Options considered:** reuse runtime evidence as the canary; live side-effecting
canary. *Rejected:* both violate PROJECT_RULES ("canaries use reserved synthetic
data, no-op/sandbox side effects").
**Why:** a control can be exercised safely even when no real invoice is flowing.
**Trade-offs:** an extra evidence stream. **Customer impact:** no unsafe customer
side effect; freshness is provable off-peak.

## D5 — Human-in-the-loop boundary that fails safe

**Decision:** `HUMAN_REVIEW`/`BLOCK` dispositions route to an idempotent human-review
ticket; if routing is unavailable, the bridge converts the typed tool error into an
`UNAVAILABLE` HITL observation, keeps the invoice blocked, retains the already-earned
PII/schema/audit evidence, and yields AMBER — never a fabricated PASS.
**Options considered:** fail-open (continue) on HITL error; drop partial evidence.
*Rejected:* both hide risk. **Why:** a consequential state must reach a person.
**Trade-offs:** an unavailable reviewer path blocks throughput (correctly).
**Customer impact:** an unsafe invoice never silently bypasses a human.

## D6 — Redaction **before** the model (the fixed defect)

**Decision:** The workflow redacts PII in the untrusted content first, builds a
**new immutable** `InvoiceInput` from the redacted text, and extracts from that; the
original is never mutated. Only boolean control metadata (`redaction_applied`, …)
crosses into evidence — never raw values, counts, keys, or reasons.
**Options considered / history:** an earlier version redacted but then extracted from
the *original* invoice, leaking raw PII to the provider. *Rejected once found:*
reproduced with a failing test, then fixed (see `ONE_DAY_AGENT_DELIVERY.md` §9).
**Why:** the model and every downstream surface must never see raw PII.
**Trade-offs:** bounded regex DLP (email/phone/account), not a complete DLP engine.
**Customer impact:** vendor personal data cannot reach a model or a retained record.

## D7 — Bounded model usage (calls, retries, tokens, timeouts)

**Decision:** One structured call per attempt; `allowed_attempts = min(max_model_calls,
max_retries+1)`; output tokens clamped; per-request timeout; Bedrock SDK retries
disabled (`total_max_attempts=1`) so no hidden client attempt bypasses the visible
cap.
**Options considered:** unbounded ret/agentic loops. *Rejected:* runaway cost.
**Why:** "no hidden cost" is a permanent promise. **Trade-offs:** a genuinely
transient blip may exhaust the small retry budget → AMBER/safe-fail.
**Customer impact:** model spend is attributable and capped; a loop can't drain a
budget.

## D8 — AWS SAM (Lambda + EventBridge), least-privilege IAM

**Decision:** Package serverless with SAM; the API function's only Bedrock action is
`bedrock:InvokeModel` scoped to `Resource: !Ref BedrockModelArn`; the scheduled
reconciliation function has **no** Bedrock permission and refreshes only the
model-free canary.
**Options considered:** always-on compute (ECS/EKS), broad `bedrock:*`, one function
for everything. *Rejected:* cost and blast radius.
**Why:** budget-conscious, least-privilege, model-resource-scoped.
**Trade-offs:** cold starts; contract/structural-tested only, not live-Lambda.
**Customer impact:** minimal attack surface and no idle spend.

## D9 — DynamoDB single-table, server-owned time

**Decision:** One tenant/environment/boundary/workflow-scoped table with server-time
TTL, transactional idempotency/evidence-ID indexes, optimistic aggregate commits,
and monotonic timeline revision. `ingested_at` is stamped by the service clock, not
the caller.
**Options considered:** relational store; caller-supplied timestamps. *Rejected:*
callers could lengthen/shorten freshness; identity spans full workflow.
**Why:** deterministic, idempotent, skew-honest persistence.
**Trade-offs:** eventual GSI visibility and live-throttling behavior remain
target-environment concerns. **Customer impact:** stale/duplicate/conflicting
evidence can't corrupt the ledger.

## D10 — API-key auth is a demonstration boundary (honest limitation)

**Decision:** Authenticate the local API with a constant-time API-key check and a
configured CORS origin.
**Options considered:** Cognito/IAM/OIDC. *Deferred, not claimed:* production
identity/authorization/rotation/quotas/WAF is out of scope for this slice.
**Why:** enough to demonstrate the boundary without over-building.
**Trade-offs:** not production identity. **Customer impact:** stated plainly so no
reviewer mistakes the demo boundary for production security.

## D11 — Privacy: metadata-only evidence, bounded errors

**Decision:** Evidence attributes are allowlisted booleans; opaque references are
SHA-256-derived and bounded; the invoice-run response is regex-constrained; API
errors return fixed codes/messages and never echo input, PII, or exception text.
**Why:** compliance evidence must be provable without storing sensitive payloads.
**Trade-offs:** less human-readable evidence (by design). **Customer impact:** no PII
in logs, evidence, API, or dashboard.

## D12 — Honest production-readiness labels

**Decision:** Every artifact is labeled Implemented / Tested / Reviewed / Planned /
Not-deployed. No claim of deployment, real-model success, production readiness, or an
MCP runtime is made.
**Why:** credibility with ex-AWS reviewers depends on not overclaiming; a package and
a green local suite are not deployment evidence.
**Trade-offs:** the story is "verified slice," not "shipped product."
**Customer impact:** decisions are made on true state, not aspiration.

---
*Interview tip: every decision has an OPTIONS-I-REJECTED-AND-WHY answer. "I chose X
over Y because Z; the trade-off was W" is what senior interviewers listen for.*
