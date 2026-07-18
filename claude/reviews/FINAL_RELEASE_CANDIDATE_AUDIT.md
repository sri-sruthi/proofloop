# ProofLoop PS-6.2 — Final Release-Candidate Audit (Track D1, independent)

**Auditor:** Claude Code (independent reviewer; agent-layer owner)
**Date:** 2026-07-18 · **Runtime:** Python 3.12.7 (Anaconda), Node 22.18.0
**Scope:** the integrated agent→ProofLoop slice (Codex Track C) plus the agent
layer, read against `docs/PROJECT_RULES.md`. The original **Track D1** pass was
review + Claude-doc only — no source/test/infra/docs/README/Codex file was
modified; no deploy, AWS/Bedrock call, or Git mutation was performed. A later
**Track E1 addendum** (bottom of this file, product-owner-authorized) records
narrowly-scoped edits to two Claude-owned files (RUFF-01, BANDIT-01).

## Method

I did not trust the handoff counts. I re-read the integration code
(`infrastructure/agent_integration.py`, `infrastructure/composition.py`,
`api/invoice_runs.py`, `api/app.py` error path, `infra/template.yaml` IAM,
`application/service.py` ingestion) and the four integration suites, then
executed the full available gate myself and ran the integrated demo.

## Verification executed (actual results)

```text
python -m pytest -q                         -> 263 passed in 1.34s
python -m mypy src/proofloop tests          -> Success: no issues (88 source files)
python -m compileall -q src tests scripts infra/scripts -> exit 0
python scripts/demo_agent_to_compliance.py  -> GREEN->AMBER->GREEN->RED->AMBER->GREEN;
   redacted-before-model=yes; injection-channel=untrusted; disposition=BLOCK;
   human-review-called=yes; bounded usage calls=1; 4 DUPLICATE on replay;
   conflict=AMBER; canary FAIL=RED; repair-only=AMBER; fresh post-repair=GREEN;
   malformed=EXTRACTION_FAILED->RED; tool failure=RECONCILIATION_FAILED->AMBER;
   no payment tool: confirmed
pytest tests/integration/test_agent_{privacy_boundary,workflow_integration,evidence_bridge,composition}.py
                                            -> 25 passed
```

Unavailable tools (no result claimed): `sam`, `ruff`, `bandit`, `pip-audit`,
`uv`, and Python 3.13. CI has not run (no Git mutation authorized). `pip check`
reports unrelated pre-existing Anaconda conflicts; not a ProofLoop dependency
claim. **No real Bedrock request was made** (stub client only).

## Audit verdict

**ACCEPT — release candidate for the requested local/stubbed slice.** Every
audited PS-6.2 safety property holds in code and under test. I found **no
Critical, Important, or Minor actionable finding** in the integrated
Claude-relevant scope. This is **not** a production-readiness, deployment, or
real-model-success statement; it matches Codex's `READY_FOR_DEPLOY` disposition
for a separately authorized first non-production deployment.

## Audited properties (each independently confirmed)

| # | Property | Evidence (file · test) | Result |
|---|---|---|---|
| 1 | Raw PII cannot reach model/evidence/API/logs/dashboard | `workflow.py` sanitized input; `agent_integration.map_control_observation` emits only boolean attrs; `invoice_runs.py` regex-bounded response; `app.py:224/237` generic errors · `test_agent_privacy_boundary`, `test_poisoned_invoice_runs_agent_to_green...` | PASS |
| 2 | Prompt injection stays untrusted data; grants no tool authority | injection in `untrusted_input` only, absent from `trusted_instructions`; no payment tool; deterministic disposition · privacy + workflow tests | PASS |
| 3 | One observation → exactly one requirement | `_MAPPING` is 1:1; `map_control_observation` · `test_each_observation_maps_to_exactly_one_runtime_requirement` (parametrized) | PASS |
| 4 | No unsupported GREEN | GREEN needs all 5 requirement-bound PASS events; deterministic evaluator · `test_poisoned_invoice...green`, spine evaluator suite | PASS |
| 5 | Stale/missing/conflicting/unavailable → AMBER | tool timeout→`REQUIRED_EVIDENCE_MISSING`; conflict→`EVIDENCE_CONFLICT`; HITL timeout→`EVIDENCE_UNAVAILABLE` · workflow tests | PASS |
| 6 | Current control failure → RED | malformed output→`CONTROL_FAILURE_OBSERVED`; canary FAIL→RED · `test_malformed_model_output...red`, canary test | PASS |
| 7 | Canary separate from runtime schema evidence | distinct `requirement_id` + `CANARY_RESULT` vs `CONTROL_OUTCOME`; separate source/provenance · `test_schema_runtime_and_canary_are_distinct_requirements` | PASS |
| 8 | Remediation cannot restore GREEN without fresh evidence | `mark_remediated`→AMBER; needs fresh post-repair canary PASS→GREEN · `test_safe_canary_red_then_remediation_amber_then_fresh_green` | PASS |
| 9 | Exact tenant/env/boundary/workflow/execution/trace correlation | `WorkflowExecutionReference` carries all six; `_stable_digest` includes all · bridge + workflow tests | PASS |
| 10 | Exact replay idempotent; contradictory replay quarantined | replay→`DUPLICATE` (count stays 5); contradiction→`EVIDENCE_CONFLICT`→AMBER, synced before stable error · `test_exact_workflow_replay_is_idempotent`, `test_runner_syncs_quarantined_conflict...` | PASS |
| 11 | Model calls/retries/tokens/timeouts bounded | cap=2 with max_retries=5; `_CappedModelProvider` clamps output tokens; Bedrock SDK retries disabled, timeouts set · `test_model_call_cap_and_tokens_are_bounded`, `test_bedrock_client_enforces_timeout...` | PASS |
| 12 | LLM cannot approve or pay | no payment tool in `APPROVED_TOOL_SPECS`; deterministic `evaluate_policy` · `test_duplicate_invoice_routes_to_hitl_and_has_no_payment_tool` | PASS |
| 13 | HITL failure preserves available evidence, fails safe | `_FailClosedHumanReviewTool`→UNAVAILABLE HITL obs, keeps 4 evidence, invoice blocked, AMBER · `test_human_review_timeout_emits_available_observations_and_fails_closed` | PASS |
| 14 | Bedrock provider state is request-scoped | fresh `BedrockConverseProvider` per run; `provider_factory` per-request · `test_bedrock_mode_uses_injected_stub...` (`first is not second`) | PASS |
| 15 | SAM IAM model-resource-scoped; scheduled fn cannot call Bedrock | API fn `bedrock:InvokeModel` → `Resource: !Ref BedrockModelArn`; scheduled fn has no bedrock action · `infra/template.yaml:169-172, 217-235`, structural test | PASS |
| 16 | No customer payload or secret in infra configuration | env-var driven; `AgentIntegrationSettings` holds version labels only; boto3 constructed lazily; no committed credential/model id | PASS |
| 17 | Customer-visible errors bounded; no exception leakage | `app.py`: `ApplicationError`→fixed message; `ValidationError`/`Exception`→generic strings; `INTEGRATION_NOT_CONFIGURED`→503 | PASS |
| 18 | Satisfies applicable PS-6.2 requirements | deterministic GREEN/AMBER/RED, requirement-bound evidence, exact provenance vector, correlation, independent canary, HITL, honest labels | PASS |

Additional confirmations: `service.ingest_evidence` re-stamps
`ingested_at = clock.now()` (`service.py:105`), so a caller cannot lengthen/shorten
freshness; dedup logical identity excludes `evidence_id`/`ingested_at`
(`memory.py:280`), which is correct for idempotency and conflict detection.

## Findings

**No Critical findings. No Important findings. No Minor findings.**

Per the review rule, I am not inventing work. The items below are
**Observations** (non-blocking notes for Codex), not defects:

### O1 — `ingested_at` set at the bridge is redundant (Observation)
- File: `src/proofloop/infrastructure/agent_integration.py:469`
  (`ingested_at=observation.observed_at`).
- Evidence: `application/service.py:105` overwrites it with the service clock, so
  the bridge value has no effect.
- Customer harm: none (behaviorally correct; freshness/skew stay service-owned).
- Owner: Codex. Acceptance test: none required; optionally delete the redundant
  assignment or assert the service re-stamp in a bridge unit test.

### O2 — provenance mismatch degrades to a generic 500 (Observation)
- File: `src/proofloop/infrastructure/agent_integration.py:444-446` raises a bare
  `ValueError` if computed provenance ≠ the declaration; `api/app.py:237` maps any
  uncaught exception to a generic 500 (no payload leaked).
- Evidence: settings are shared between definition and emitter, so this path is
  unreachable in normal operation; it is defense-in-depth.
- Customer harm: none today (no leak; correct fail-closed). A future drift would
  surface as an opaque 500 rather than a typed, explainable error.
- Owner: Codex. Acceptance test (only if hardening): raise a typed
  `ApplicationError` and assert a bounded 4xx/5xx with a stable code.

### O3 — carry-forward honest limitations (Observation, already disclosed)
- Bounded regex redactor is not full DLP; in-memory business tools (no MCP
  runtime / live AP-ERP); API-key auth is not production identity/authz/rotation/
  WAF/quotas; DynamoDB/SAM are contract/structural-tested, not live-table/live-
  Lambda; the invoice endpoint has no caller run-key, so a re-execution is a new
  observation, not a command retry; no real AWS/Bedrock/accuracy/latency/cost
  evidence. Owner: Codex/product owner. These are limitations to state honestly in
  the submission, not defects to fix for the slice.

## PS-6.2 permanent-promise mapping

No unsupported green (#4), no surprise shutdown (#5,#13 AMBER + safe action), no
black-box score (#3,#17 reason codes + bounded messages), no vendor lock-in
(#14,#15 neutral seam, no boto3 in core), no hidden cost (#11 bounded caps/tokens),
no unsafe canary (#7 synthetic + side_effects_absent), no premature recovery
(#8). All hold.

## Files changed by this task

- `claude/reviews/FINAL_RELEASE_CANDIDATE_AUDIT.md` (this file)
- `claude/DECISIONS.md` (rewritten for canonical PS-6.2)
- `claude/FINAL_DEMO_AND_INTERVIEW_NARRATIVE.md` (new)
- `claude/handovers/FINAL_AGENT_AND_SUBMISSION_NARRATIVE.md` (stale "not
  integrated" wording corrected)

No `src/**`, `tests/**`, `infra/**`, `docs/**`, `README.md`, or `codex/**` file
was modified.

## Remaining blockers

- **None for the requested local/stubbed slice.** For a first non-production
  deployment the product owner must still authorize deployment and supply AWS
  account/region/stack, API-key delivery, Bedrock model/inference-profile ID +
  least-privilege ARN, call/timeout limits + spend alarm, allowed origin, and CI/
  SAM-validate results. These are authorizations, not code defects.
- **AWS account status (updated 2026-07-18):** the earlier payment-method
  verification block is **resolved** — the AWS Free account is now activated and
  the Lambda console opens successfully in `ap-south-1`. **AWS deployment and real
  Bedrock execution have still NOT occurred** and remain gated on the explicit
  authorization + clean Python-3.13/SAM evidence above.

## Recommended next Codex actions

1. Optional hygiene: O1 (drop redundant `ingested_at`) and O2 (typed error on
   provenance drift).
2. When AWS is authorized and payment verified: run the CI matrix + `sam validate`
   + container build, then a single scoped Bedrock smoke via
   `scripts/smoke_bedrock_invoice.py` (gated by `PROOFLOOP_ALLOW_REAL_MODEL_SMOKE`).
3. Consider a caller run-key for the invoice endpoint to make re-execution a
   command retry rather than a new observation.

## Five files I read for the interview

1. `src/proofloop/infrastructure/agent_integration.py`
2. `src/proofloop/api/invoice_runs.py`
3. `tests/integration/test_agent_privacy_boundary.py`
4. `tests/integration/test_agent_workflow_integration.py`
5. `infra/template.yaml`

---

# Track E1 addendum — Claude-owned release-blocker repairs (2026-07-18)

**Authorization:** explicit product-owner Track E1 authorization, scoped to the two
Claude-owned findings below only. **Constraints honored:** no domain/application/
infrastructure/API/SAM/docs/Codex file touched; no deploy, AWS/Bedrock call, Git
commit/push, or GitHub resource. Sources cross-referenced:
`codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md` (gate matrix: RUFF BLOCK,
BANDIT BLOCK).

## Findings repaired

### RUFF-01 (F401) — fixed
- `src/proofloop/agents/workflow.py:28` — removed the unused `ExtractedInvoice`
  import (the only remaining occurrence, line 344, is inside a docstring/string
  literal, not a symbol reference — verified by grep). `Disposition` and
  `InvoiceInput` remain because they are used.

### BANDIT-01 (B105) — suppressed narrowly, contract preserved
- `src/proofloop/agents/guardrails.py:40` — `ControlOutcome.PASS = "PASS"` is an
  assurance-outcome enum member, **not** a password, and its serialized value is a
  contract consumed by the evidence bridge (`ControlOutcome.value` →
  `EvidenceOutcome`). Added the **narrowest** documented inline suppression,
  `# nosec B105`, with an explanatory comment. The enum member and its literal
  value are unchanged; B105 is **not** disabled globally. (The sibling literal at
  `src/proofloop/domain/models.py:44` is Codex-owned and intentionally left for
  its owner.)

### Test added (TDD)
- `tests/agents/test_agent_guardrails.py::test_control_outcome_pass_serializes_exactly_as_the_string_pass`
  — asserts `ControlOutcome.PASS.value == "PASS"` and that a serialized
  `ControlObservation` contains `"outcome":"PASS"`, pinning the contract the
  suppression guards.

## Exact commands and outcomes (Python 3.12.7, `/opt/anaconda3/bin/python3`)

```text
pytest tests/agents/…::test_control_outcome_pass_serializes… -q -> 1 passed
pytest tests/agents -q                        -> 99 passed
pytest -q                                     -> 266 passed
mypy src/proofloop/agents tests/agents        -> Success: no issues (31 source files)
compileall src/proofloop/agents tests/agents  -> exit 0
ruff  check src/proofloop/agents tests/agents -> NOT RUN — ruff not installed
                                                 (no module, not on PATH, no venv)
bandit -q -r src/proofloop/agents             -> NOT RUN — bandit not installed
                                                 (no module, not on PATH, no venv)
python -m pip list | grep -iE '^ruff|^bandit' -> neither installed
```

**Ruff/Bandit honesty:** both tools are unavailable in this local Anaconda
environment and I did not install software (unauthorized). I therefore make **no**
claim that a green Ruff/Bandit run was observed. The fixes are correct-by-
construction and consistent with the exact findings Codex's isolated CI-like
environment reported:
- RUFF-01 was the only Ruff finding in Claude-owned scope (F401); it is removed, so
  a subsequent Ruff run over `src/proofloop/agents` should no longer report it.
  (The remaining gate Ruff findings — E731 at `composition.py:144/161` — are
  infrastructure-owned and out of this task's scope.)
- BANDIT-01 for `guardrails.py` now carries `# nosec B105`, which Bandit honors as
  a line-scoped suppression of exactly that test. Codex should re-run
  `bandit -q -r src/proofloop/agents` in the CI-like environment to confirm a clean
  exit for the agent package.

## Files changed by Track E1

- `src/proofloop/agents/workflow.py` (removed unused import)
- `src/proofloop/agents/guardrails.py` (`# nosec B105` + explanatory comment)
- `tests/agents/test_agent_guardrails.py` (added focused contract test + import)
- `claude/reviews/FINAL_RELEASE_CANDIDATE_AUDIT.md` (this addendum + AWS-status
  correction)

## Unresolved / not-owned by Track E1

- **RUFF E731** (`composition.py:144,161`) — infrastructure owner.
- **BANDIT B105** (`domain/models.py:44`) — domain owner (same narrow-suppression
  pattern recommended).
- **AUDIT-01** (pytest 8.4.2 / PYSEC-2026-1845) — dependency-policy owner.
- **TOOLING-01 / REPO-01** — Python 3.13, SAM, GitHub baseline/CI — deployment &
  product owner.
- Local **Ruff/Bandit execution** — needs the CI-like environment (or authorized
  local install) to produce a green transcript for the two repaired findings.
