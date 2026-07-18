# ProofLoop PS-6.2 — Final Demo & Interview Narrative

*Aligned with the **integrated** state (Codex Track C): agent → requirement-bound
evidence → deterministic compliance. Verified 2026-07-18: 277 tests pass, mypy
clean (89 files), after Codex G1.6 infrastructure hardening (alarms/SNS/origin/
default-disabled schedule). The code/packaging gate is green in a **private-repo CI matrix**
across Python 3.12 (x64) and native **ARM64 Python 3.13**, with Ruff, Bandit, a
strict dependency audit, and **SAM validate/build + both built-handler imports**
passing. Still **not deployed, no real Bedrock call, not production-ready, no MCP
runtime.***

---

## 1. Beginner analogies

- **ProofLoop = a surprise health inspector, not the certificate on the wall.** A
  restaurant hangs a "kitchen inspected & clean" certificate (the *config*).
  ProofLoop walks in unannounced and checks the fridge temperature *today*. Fresh
  passing reading → **GREEN**. Reading from last week, or from a different
  restaurant, or thermometer unplugged → **AMBER: can't confirm it's safe right
  now** (not "fine", not "shut it down"). Measurably too warm → **RED**.
- **Extraction agent = a careful data-entry clerk** (reads the invoice into a strict
  form, flags anything unreadable, has no cheque book).
- **Reconciliation agent = a matching clerk** (checks the form against the official
  PO book and vendor list, records disagreements, also can't sign a cheque).
- **Policy = the rulebook** (fixed rules → proceed / send to a human / block).
- **Guardrail middleware = a safety inspector's checklist** (PII blacked out? audit
  line written? risky decision sent to a human? output passed the strict form?).
- **Evidence bridge = a notary** who converts each checklist stamp into one sealed,
  tamper-evident record filed against exactly one obligation.
- **ProofLoop evaluator = a deterministic auditor** who turns those records into
  GREEN/AMBER/RED with reasons — and refuses green without fresh, matching proof.

## 2. What each component does

- `InvoiceInput` — separates *trusted* operator metadata from *untrusted* document
  text.
- `GuardrailMiddleware` — deterministic, free controls: PII redaction,
  extraction-schema validation, HITL boundary, audit logging → agent-neutral
  `ControlObservation`s.
- `run_extraction` — one bounded structured model call through the neutral
  `ModelProvider` seam; output untrusted until it passes the strict `ExtractedInvoice`
  schema (Decimal totals must reconcile).
- `run_reconciliation` — deterministic; pulls authoritative facts from four typed
  tools, computes typed mismatches.
- `evaluate_policy` — pure function → `ACCEPT_FOR_POLICY_EVALUATION` / `HUMAN_REVIEW`
  / `BLOCK` (ACCEPT ≠ payment).
- `run_invoice_workflow` — sequences the above under hard caps; sanitizes PII before
  the model; routes unsafe states to a human.
- `agent_integration` (infra) — maps each observation to exactly one
  requirement-bound `EvidenceEnvelope` (boolean attributes only), runs an independent
  synthetic canary, ingests, syncs.
- `ProofLoopService` + domain evaluator — deterministic GREEN/AMBER/RED with reason
  codes, timeline, incidents; server-owned `ingested_at`.
- `BedrockConverseProvider` — real-model boundary; injected client, no boto3 in core.
- SAM/Lambda/DynamoDB — least-privilege serverless package (not deployed).

## 3. What I personally engineered (Claude-owned agent layer + audits)

- The agent business core: immutable Pydantic contracts (Decimal money, UTC),
  `ExtractedInvoice` arithmetic invariants, the two bounded agents, and the pure
  `evaluate_policy`.
- The `ModelProvider` seam, the deterministic `FakeModelProvider`, and the
  cloud-neutral `BedrockConverseProvider` (injected client, typed error mapping).
- Versioned prompts with content hashing; the four MCP-ready tool specs (no payment
  tool).
- `GuardrailMiddleware` (PII redaction + three controls) and the bounded
  `run_invoice_workflow` orchestrator with recording wrappers for provenance-grade
  telemetry.
- **Found and fixed a real defect:** raw PII was reaching the model because the
  workflow extracted from the original invoice; reproduced with a failing test,
  fixed by extracting from a sanitized immutable input.
- Independent reviews: the foundation review (found B1 + H1–H9), the agent⇄domain
  compatibility review, and this release-candidate audit.
  *(Codex owns the domain/application/infrastructure/API/SAM integration.)*

## 4. Why two agents are justified

Extraction and reconciliation have **different inputs, trust models, and failure
modes.** Extraction consumes untrusted document text and needs a model;
reconciliation consumes authoritative tool records and is deterministic. Splitting
them caps the model's blast radius to "read text → fields" and lets
reconciliation/policy be provably deterministic. A manipulated extraction cannot
rewrite a PO total because matched facts come only from tools. A third agent was
deliberately not added.

## 5. Where data science appears (honestly)

The verdict is deliberately **deterministic** — no ML touches GREEN/AMBER/RED. Data
science shows up around the edges and in the roadmap:

- **Calibration:** `model_reported_confidence` is treated as *uncalibrated* and
  labeled as such; turning it into a trustworthy probability is an evaluation-harness
  task (reliability curves, Brier score) — future work, never a gate today.
- **Threshold selection as a cost trade-off:** the policy's amount tolerance,
  confidence threshold, and high-value threshold are explicit false-positive vs
  false-negative decisions — the same discipline as setting a detector's operating
  point ("a detector that cries wolf gets turned off").
- **Evaluation design:** measuring extraction accuracy needs a labeled dataset and
  metrics; the current fixtures are explicitly *not* a dataset and make no accuracy
  claim.
- **Continuous validation:** the synthetic canary is a control-health signal, akin to
  a data-quality monitor that runs even when no real traffic flows.
- **Roadmap:** the regex redactor could become an ML NER redactor, and extraction an
  evaluated model — but both would emit *evidence*, never the verdict.

This is the defensible DS story: I know exactly where probabilistic methods belong
(support, calibration, evaluation) and where they must be fenced out (the auditable
gate).

## 6. Customer story

An accounts-payable team declares three controls: "we redact PII," "a human approves
risky invoices," "everything is audit-logged." Six weeks later a config drift quietly
disables redaction. The monitoring dashboard stays green because it reports the
*setting*. With ProofLoop, the PII-redaction control only earns GREEN when a fresh
runtime event proves redaction actually ran on this execution; the moment the proof
goes missing or stale, the customer sees **AMBER with a reason and a safe next
action** — before a vendor's bank details leak into a model or a log. The AP owner
trusts green because green means *proven-now*, not *configured-once*.

## 7. Market differentiation

- **vs AI-safety / observability dashboards:** they report configuration and stay
  green after a control silently stops firing. ProofLoop verifies *execution*
  continuously and refuses green without fresh, correlated PASS evidence.
- **vs LLM-as-judge evaluators:** non-reproducible and biased on identical inputs;
  ProofLoop's verdict is a deterministic reduction, and even the invoice disposition
  is a pure function.
- **vs static GRC / compliance tooling:** attests to policies and past audits (the
  certificate); ProofLoop checks *today's* reading, bound to this exact
  tenant/environment/assurance-boundary execution with an exact provenance vector, so
  staging evidence or a downgraded guardrail cannot green production.

## 8. Explanations

**30 seconds:**
> "ProofLoop continuously proves whether an AI agent's declared safety controls are
> actually running now — not just configured. I built the invoice agent layer: PII is
> stripped before the model, extraction output is strictly validated, the decision is
> a deterministic policy (the LLM never approves or pays), and every control emits one
> requirement-bound piece of runtime evidence. A deterministic evaluator returns GREEN
> only when every obligation has fresh passing proof; missing or ambiguous proof is
> AMBER, a real failure is RED."

**2 minutes:**
> "The reference workload is invoice processing. `InvoiceInput` separates trusted
> metadata from untrusted document text. A deterministic guardrail redacts PII, and
> the workflow extracts from a *sanitized* copy — I caught and fixed a bug where the
> original was being sent, so raw PII now never reaches the model. Extraction makes one
> bounded call through a neutral provider seam; the output is untrusted until it passes
> a strict schema whose Decimal totals must reconcile. Reconciliation pulls
> authoritative facts from four typed tools and treats them as untrusted data, so a
> manipulated extraction can't rewrite a PO total. A pure policy function decides:
> unknown vendor or confirmed duplicate blocks; missing PO, mismatch, low confidence,
> or high value goes to a human; otherwise it's accepted only for the next policy
> stage — never payment. Then the integration maps each guardrail observation to
> exactly one requirement-bound evidence event carrying only booleans plus an exact
> provenance vector, adds an independent synthetic canary, and the deterministic
> ProofLoop evaluator produces GREEN/AMBER/RED with reason codes. If the human-review
> path is unavailable, it fails safe — keeps the invoice blocked, retains the evidence
> already earned, and goes AMBER. Model calls, retries, and tokens are hard-capped;
> there's no payment tool anywhere; and the whole thing is cloud-neutral — a Bedrock
> adapter takes an injected client with no boto3 in the core. It's a locally verified
> slice: no real AWS call, not deployed."

**Deep technical:**
> "Identity is exact: tenant, environment, assurance boundary, workflow, execution,
> trace. Each requirement owns a ten-field provenance vector (component, prompt,
> provider/model, policy, schema, tool-catalog, MCP=None, orchestration, guardrail,
> runtime-config); ingestion rejects drift. Evidence is metadata-only: allowlisted
> booleans and SHA-256-derived bounded references, with logical identity excluding the
> outcome so contradictory reuse is a *conflict* (quarantined → AMBER) rather than a
> silent overwrite. `ingested_at` is stamped by the service clock, so a caller can't
> lengthen or shorten freshness; skew tolerance defaults to five seconds and raw
> timestamps are preserved. PASS is the only GREEN-supporting outcome; INCOMPLETE/
> UNAVAILABLE are AMBER; a current FAIL is RED. Remediation sets a strict verification
> boundary and stays AMBER until fresh post-repair PASS *and* a fresh synthetic canary
> PASS arrive — equality with the boundary is insufficient. The canary is independent,
> synthetic, model-free, side-effect-free, and typed `CANARY_RESULT`, never relabeled
> runtime proof. SAM IAM grants exactly one `bedrock:InvokeModel` scoped to the model
> ARN; the scheduled function has no Bedrock permission and refreshes only the canary,
> with SDK retries disabled so no hidden attempt bypasses the agent's visible call
> cap."

## 9. Likely senior (ex-AWS) questions — defensible answers

- **"How do you prevent a false green?"** GREEN needs every requirement's fresh,
  correlated, provenance-matched PASS; the reducer is deterministic and pure;
  probabilistic signals never declare GREEN. Tested by the AMBER/RED paths.
- **"Prove the model can't run away with cost."** `min(max_model_calls, max_retries+1)`;
  a timeout-forever provider with 5 retries still stops at 2 calls; Bedrock SDK
  retries disabled and timeouts set.
- **"What stops PII reaching Bedrock or your logs?"** Redaction before extraction on a
  sanitized immutable input; evidence carries booleans only; the response is
  regex-bounded; errors never echo input/exception. A cross-layer test inspects the
  provider request, evidence store, API, Lambda body, dashboard, and logs.
- **"Why not LLM-as-judge for the verdict?"** Non-reproducible and biased on identical
  inputs; a payment gate must be deterministic and auditable.
- **"Least privilege for Bedrock?"** One `bedrock:InvokeModel` action scoped to
  `!Ref BedrockModelArn`; scheduled function has none.
- **"How is this not just a dashboard?"** Dashboards report configuration; ProofLoop
  binds each proof to one requirement and one exact execution and refuses green
  without fresh matching evidence.
- **"What's not done?"** No AWS deployment and no real Bedrock call yet — hence no
  accuracy/latency/cost evidence from a live model or live DynamoDB/EventBridge.
  (What *is* done: private-repo CI on Python 3.12 + native ARM64 3.13, SAM
  validate/build, and both built-handler imports.) Other honest limits: bounded
  regex DLP; in-memory tools / no MCP runtime; API-key demo auth; no caller run-key
  on the invoice endpoint yet. Stated up front.
- **"Where's the data science?"** Calibration, threshold trade-offs, evaluation
  design, and continuous validation — all fenced out of the deterministic verdict (see
  §5).

## 10. 5–8 minute demo narration (integrated)

1. **(0:00–0:40) Framing.** "Dashboards tell you a control is *configured*. ProofLoop
   proves it's *executing*." Show `docs/PROJECT_RULES.md` promises: no unsupported
   green, no surprise shutdown, no black-box score.
2. **(0:40–1:40) One poisoned invoice, end to end.** Run
   `python scripts/demo_agent_to_compliance.py`. Narrate the printed line
   `redacted-before-model=yes; injection-channel=untrusted`. Show the provider request
   has `[REDACTED_EMAIL]`/`[REDACTED_ACCOUNT]` and the injection sits in the untrusted
   channel only. "The model never sees PII; the injection is inert data; there is no
   payment tool."
3. **(1:40–2:40) Agent controls become evidence → GREEN.** Show `calls=1`, four runtime
   evidence receipts plus one independent canary, and `overall_compliance_status GREEN`.
   "Green here means proven-now: four requirement-bound events and a synthetic canary."
4. **(2:40–3:40) The safety envelope.** Duplicate invoice → `disposition=BLOCK`,
   human-review called; then human-review timeout → fails safe, keeps evidence, AMBER
   `EVIDENCE_UNAVAILABLE`. "An unsafe state can never silently bypass a human."
5. **(3:40–4:40) The honesty envelope.** Idempotent replay → 4 DUPLICATE; contradictory
   replay → quarantine → AMBER `EVIDENCE_CONFLICT`; malformed output → RED
   `CONTROL_FAILURE_OBSERVED`; tool failure → AMBER `REQUIRED_EVIDENCE_MISSING`.
6. **(4:40–5:40) No premature recovery.** Canary FAIL → RED; `mark_remediated` → AMBER;
   only a *fresh* post-repair runtime PASS + canary PASS → GREEN. Show the printed path
   `GREEN -> AMBER -> GREEN -> RED -> AMBER -> GREEN`.
7. **(5:40–6:40) Cloud-neutral + least privilege.** Show `BedrockConverseProvider` with
   an injected stub (no boto3 in core) and `infra/template.yaml`: one model-scoped
   `bedrock:InvokeModel`, scheduled function has none. State plainly: **not deployed,
   no real Bedrock call, API-key demo auth.**
8. **(6:40–7:30) Close.** "266 tests, deterministic verdict, no PII leak, LLM fenced
   out of every consequential decision — a verified slice that earns green honestly."

---
*Every claim here maps to a passing test or an inspected artifact; nothing asserts
deployment, a real-model result, production readiness, or an MCP runtime.*
