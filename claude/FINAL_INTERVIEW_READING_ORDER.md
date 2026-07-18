# ProofLoop PS-6.2 — Final Interview Reading Order

*A sequenced path to walk in able to explain and defend the solution — beginner
framing first, then depth, then the honest edges. Read in this order. Everything
here is already true of the repo as of 2026-07-18 (266 tests pass locally).*

---

## Phase 0 — the one-paragraph anchor (2 min)

Read the **README.md** top block. Memorize the thesis:
> "Dashboards report what a control was *configured* to do; ProofLoop proves what
> it is *actually doing right now*. GREEN only with fresh, correlated PASS
> evidence; missing/stale/ambiguous → AMBER; a confirmed failure → RED."

## Phase 1 — plain-English understanding (15 min)

1. **`claude/FINAL_DEMO_AND_INTERVIEW_NARRATIVE.md`** — analogies (§1), what each
   component does (§2), what the LLM can/can't do (§4), the five controls (§5),
   why two agents (§7), where data science appears (§5), market differentiation
   (§7), and the 30-sec / 2-min / deep answers (§8). *This is your spine.*
2. **`docs/submission/DEMO_RUNBOOK.md`** — the exact demo you will narrate. Note the
   states: GREEN → (duplicate) BLOCK+HITL → replay DUPLICATE → conflict AMBER →
   canary RED → remediation AMBER → fresh GREEN.

## Phase 2 — the "why" behind every choice (15 min)

3. **`claude/DECISIONS.md`** — D0–D12 with options-rejected. The ones interviewers
   probe most: D1 (deterministic verdict, not LLM-judge), D2 (two agents),
   D3 (one event → one requirement), D4 (independent canary), D6 (redaction
   *before* the model — the bug you found and fixed), D7 (bounded model cost).
4. **`docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.md`** — §2 fifth element,
   §6 deterministic assurance, §8 privacy/injection, §11 AWS architecture,
   **§12 market comparison**, §15 limitations. This is the evaluator's document —
   know it cold.

## Phase 3 — prove you own the code (25 min)

Read these five files and be ready to whiteboard the flow between them:

5. `src/proofloop/agents/workflow.py` — redaction-before-model; sanitized
   immutable `InvoiceInput`; bounded extraction; deterministic policy; HITL routing.
6. `src/proofloop/agents/guardrails.py` — the four controls; PII redaction;
   metadata-only observations; `ControlOutcome.PASS == "PASS"` contract.
7. `src/proofloop/infrastructure/agent_integration.py` — one observation → one
   requirement-bound `EvidenceEnvelope`; boolean-only attributes; the safe-canary;
   provenance vector.
8. `src/proofloop/application/models.py` — `ComplianceReadModel` with the **exact
   PS-6.2 field names** (`guardrails_active`, `last_violation_timestamp`,
   `pii_redaction_enabled`, `audit_logging_enabled`, `hitl_configured`,
   `overall_compliance_status`).
9. `tests/integration/test_ps62_acceptance.py` — the four success criteria mapped
   to named tests. Open this if asked "how do you know it meets the spec?"

## Phase 4 — the honest edges (10 min)

10. **`claude/reviews/FINAL_SUBMISSION_AUDIT.md`** (this track) — the traceability
    table, the **SC2 fidelity note** (silent→AMBER, explicit failure→RED), and the
    production-readiness scoring gap.
11. **`codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`** — the blocker map and
    what is *not* done (Python 3.13, SAM build, CI, AWS, real Bedrock). *(Note: this
    doc is stale on counts — see audit F-2; trust MANUAL_QA_EVIDENCE for numbers.)*

---

## Five answers to have word-perfect

- **"What did you personally build?"** → "The invoice agent layer and its safety
  contracts: the two-agent design, the deterministic policy, the guardrail
  middleware, the cloud-neutral model-provider seam and Bedrock adapter — and I
  found and fixed a real defect where raw PII was reaching the model. I also ran
  the independent audits." *(Don't claim the domain/application/infra — that's the
  Codex-owned spine; owning your boundary honestly is more credible.)*
- **"Deterministic or AI?"** → "The verdict and the invoice disposition are
  deterministic pure functions. The LLM only reads untrusted text into a strict
  schema. Probabilistic signals can support but never declare GREEN."
- **"How is this not a dashboard?"** → "A dashboard reports configuration and stays
  green after a control silently fails. We bind each proof to one requirement and
  one exact execution, and refuse green without fresh matching evidence."
- **"Red within 48h?"** (SC2) → the fidelity answer: "A silent failure is AMBER —
  we can't *confirm* failure from absence. A real failure signal, our synthetic
  canary at hour 48, drives RED, and sustained AMBER opens an SLA incident. That's
  'no unsupported green, and no unsupported red.'"
- **"Is it production-ready?"** → "No, and I won't claim it. It's a locally verified
  slice — 266 tests, deterministic, privacy-safe. AWS deployment, real Bedrock, and
  the Python-3.13/SAM/CI gate are the documented next steps. The assignment rewards
  deployment and a real LLM; that's my honest gap and my roadmap closes it."

## Do-not-overclaim list (say these boundaries out loud in the video)

- Not deployed; no real AWS resource created.
- No real Bedrock call — the adapter is stub-tested with an injected client.
- Business tools are in-memory; no MCP runtime; API-key auth is a demo boundary.
- Fixtures are not a dataset; model confidence is uncalibrated.
- AI coding assistance was used and is disclosed, not hidden.
