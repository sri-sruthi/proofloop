# ProofLoop Foundation — Independent Contract & Customer-Safety Review

**Reviewer:** Claude Code (independent contract / production-readiness / customer-safety / agent-integration gate)
**Date:** 2026-07-18
**Scope:** Codex-authored domain foundation (`src/proofloop/domain/*`, `tests/domain/*`, `pyproject.toml`, `docs/PROJECT_RULES.md`, contracts plan).
**Mode:** Review-only. No source or tests modified. No commit/push/deploy/install. Findings verified by running the code, not by trusting prior reports.

---

## 1. Executive verdict

**CONDITIONAL GO.**

The foundation is unusually strong for a first slice: cloud-neutral, immutable, UTC-strict, event-time ordered, deterministic, and it already blocks the obvious unsupported-GREEN paths for a *single-requirement* control. `mypy` is clean, all 23 tests pass, and the domain imports zero AWS/LLM/MCP/network code. That is real engineering, not boilerplate.

But the central product promise — **"no unsupported green"** — is **falsifiable today**, and I reproduced it:

> A control that declares **two** evidence requirements of the **same `evidence_type` and `source`** is reported **GREEN when only one evidence event exists.** One event silently satisfies both obligations.

This is a **Blocking** contract defect because the agent layer (Claude-owned) will *emit* the evidence these requirements bind to. If Claude builds evidence-emission against the current schema, agents will produce false green. The fix is a schema change (`requirement_id`/subject on evidence, or a predicate binding), so it must land **before** any agent evidence-emission code is written.

Therefore: **agents may begin in strict isolation** (model provider + agent business logic + prompts + MCP tool signatures), but **no evidence/provenance/workflow-reference emission code** until the disputed contracts (Findings B1, H5, H6) are frozen by Codex. Exact allowed file list in §9.

I am **not** issuing GO merely because tests pass — the passing tests do not cover the multi-requirement, `minimum_count>1`, boundary-equality, or simultaneous RED+AMBER dimensions where the defect lives (Finding H8).

---

## 2. Verified baseline

All commands run by me on 2026-07-18; outputs are actual.

| Check | Command | Result |
|---|---|---|
| Declared runtime | `pyproject.toml` | `requires-python = ">=3.13"` |
| **Actual tested runtime** | `/opt/anaconda3/bin/python3 --version` | **Python 3.12.7** — 3.13 was **never** executed |
| Interpreter running the suite | `python -c "import sys; print(sys.executable)"` | `/opt/anaconda3/bin/python3` (global Anaconda) |
| Tests | `/opt/anaconda3/bin/python3 -m pytest -q` | **23 passed in 0.14s** |
| Type check | `mypy src/proofloop` (mypy 1.11.2) | **Success: no issues found in 5 source files** |
| Byte-compile | `python -m compileall -q src tests` | exit 0 |
| Domain import-leak scan | `grep -rniE "boto3|aws|langchain|openai|anthropic|mcp|bedrock|requests|httpx|socket" src/proofloop/` | **none found** — core is clean |
| pydantic | import | 2.13.4 (Anaconda) / 2.12.5 (framework py) — pyproject pins `>=2.12,<3` ✅ |
| Env isolation | `find` | **No project-local venv, no lockfile.** Suite depends on the **global Anaconda** environment. |
| Declared test deps | `pyproject.toml [test]` | only `pytest`. **`mypy`, `ruff`, `hypothesis` are NOT declared.** `ruff` is **not installed at all**; no lint config exists. |
| Baseline commit | `git log` | **"No commits yet."** Repo is entirely untracked. |
| Repo hygiene | `find` | `.DS_Store`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` present and **untracked; no `.gitignore`.** |

**Interpretation:** the verification that has actually happened is "Python 3.12.7 + Anaconda-global pydantic/pytest/mypy, no lint, no lockfile, no commit." Any claim of 3.13 support, lint-clean, or reproducibility is currently **unproven**.

---

## 3. Blocking findings

### B1 — One evidence event satisfies multiple same-type requirements → confirmed unsupported GREEN
- **Severity:** Blocking
- **Location:** `src/proofloop/domain/evaluator.py:159-168` (requirement→event matching) with `src/proofloop/domain/models.py:160-183` (`EvidenceEnvelope` carries no `requirement_id`) and `models.py:123-141` (`RequiredEvidenceSpecification`).
- **Failure scenario (reproduced):** A control `payment-guard` declares two requirements — `redaction-check` and `approval-check` — both `evidence_type=CONTROL_OUTCOME`, both `required_source="runtime"`. Only **one** PASS event exists. `_evaluate_requirement` matches events purely by `control_id + evidence_type + source`, so the *same single event* matches *both* requirements; both findings are GREEN; the control reduces to **GREEN**. Live output:
  `status with 1 event for 2 requirements: AssuranceStatus.GREEN | considered: ('only-one',)`
- **Customer/production impact:** Persona = the deploying customer/operator relying on the green light before releasing payment. Harm = **the platform certifies two independent controls as verified when only one produced evidence** — the exact "unsupported green" the product exists to prevent. In the invoice workflow, an unverified human-approval control could read GREEN off a redaction event. The customer receives a confident green with no signal that a distinct obligation was never observed.
- **Minimal correction (Codex):** Bind evidence to the requirement it satisfies. Cheapest safe option: add `requirement_id: Identifier` to `EvidenceEnvelope` and match on it; or add a typed `subject`/`assertion` (e.g., an `assertion_key`) to both `RequiredEvidenceSpecification` and `EvidenceEnvelope` and require equality. Reject/AMBER any requirement with zero events bound to *its* id. This is a contract change agents must honor when emitting evidence — hence Blocking, not High.
- **Regression test:** `test_two_same_type_requirements_need_two_bound_events` — control with two `CONTROL_OUTCOME`/same-source requirements, supply one event bound to requirement A only, assert **AMBER** with `REQUIRED_EVIDENCE_MISSING` naming requirement B; then supply two correctly-bound events and assert GREEN.
- **Owner:** Codex (schema + evaluator). Claude consumes downstream.

---

## 4. High findings

### H1 — `accepted_outcomes` is a public contract that is silently ignored
- **Severity:** High
- **Location:** `models.py:131-141` (field advertised, validated non-empty) vs `evaluator.py:243-267` (FAIL→RED, INCOMPLETE→AMBER, UNAVAILABLE→AMBER are decided *before* `accepted_outcomes` is consulted).
- **Failure scenario (reproduced):** `accepted_outcomes=(PASS, INCOMPLETE)` → an INCOMPLETE event still returns **AMBER/EVIDENCE_INCOMPLETE**. `accepted_outcomes=(FAIL,)` → a FAIL event still returns **RED**. Only `PASS` is ever honored; every other configured value is dead. A config can appear supported while being ignored.
- **Customer/production impact:** An operator who configures "INCOMPLETE is acceptable for this best-effort control" gets AMBER anyway and cannot understand why — a **black-box surprise** that erodes trust in the very explainability the product sells. Worse in reverse: a reviewer could *believe* they narrowed acceptance and be silently overruled.
- **Minimal correction (Codex):** Decide one model and make it true. Either (a) delete `accepted_outcomes`, hard-code PASS semantics, and document it; or (b) genuinely honor it — consult `accepted_outcomes` first, and **reject at construction** any spec whose accepted set would be unreachable (e.g., forbid `FAIL` in `accepted_outcomes`, since FAIL→RED is a safety invariant).
- **Regression test:** `test_accepted_outcomes_is_honored_or_rejected` — assert either a `ValidationError` on illegal accepted sets, or that a legal non-PASS accepted outcome actually changes the result.
- **Owner:** Codex.

### H2 — `AssuranceEvaluation` / `StateTransitionExplanation` permit self-contradictory objects
- **Severity:** High
- **Location:** `models.py:185-206`.
- **Failure scenario (reproduced):** `AssuranceEvaluation(status=GREEN, explanation=<current_status=RED,…>)` is accepted. A `StateTransitionExplanation(current_status=GREEN, reason_codes=(CONTROL_FAILURE_OBSERVED,))` is accepted. The evaluator always builds these consistently, but the **contract** does not, and the API adapter / customer-explanation layer (Claude-owned) will construct them independently.
- **Customer/production impact:** A serialization that says `status: GREEN` while the human-readable body says "a current control failure was observed" — a **black-box / contradictory** customer message, and a channel for shipping green over a red truth.
- **Minimal correction (Codex):** `model_validator(mode="after")` on `AssuranceEvaluation` asserting `status == explanation.current_status`; on `StateTransitionExplanation` assert GREEN ⇒ `reason_codes == (ALL_REQUIRED_EVIDENCE_VERIFIED,)` and `affected_control_ids == ()`, and non-GREEN ⇒ at least one affected control.
- **Regression test:** `test_assurance_evaluation_status_matches_explanation` and `test_green_explanation_forbids_failure_reasons` — assert `ValidationError`.
- **Owner:** Codex.

### H3 — `IncidentRecord` can be RESOLVED with no resolution evidence (premature recovery)
- **Severity:** High
- **Location:** `models.py:209-221` (`resolution_evidence_ids` defaults to `()`).
- **Failure scenario (reproduced):** `IncidentRecord(status=RESOLVED, resolution_evidence_ids=())` is accepted.
- **Customer/production impact:** Directly violates permanent promise **"no premature recovery."** An incident can be closed with zero proof of fix; the customer sees "resolved" without evidence.
- **Minimal correction (Codex):** `model_validator` — `status == RESOLVED ⇒ len(resolution_evidence_ids) >= 1`.
- **Regression test:** `test_resolved_incident_requires_resolution_evidence`.
- **Owner:** Codex.

### H4 — `CanaryResult` can be PASS while side effects are not confirmed absent (unsafe canary passes)
- **Severity:** High
- **Location:** `models.py:236-255`.
- **Failure scenario (reproduced):** `CanaryResult(outcome=PASS, side_effects_confirmed_absent=False)` is accepted.
- **Customer/production impact:** Violates permanent promise **"no unsafe canary."** A canary that could not prove it left no side effects is nonetheless recorded as a clean PASS and could feed recovery.
- **Minimal correction (Codex):** `model_validator` — `outcome == PASS ⇒ side_effects_confirmed_absent is True`.
- **Regression test:** `test_passing_canary_requires_confirmed_no_side_effects`.
- **Owner:** Codex.

### H5 — No environment / deployment isolation; non-prod evidence can satisfy a prod control
- **Severity:** High (freeze the boundary before agent evidence emission)
- **Location:** `models.py:101-107` (`WorkflowExecutionReference` = tenant/workflow/execution/trace only).
- **Failure scenario:** Correlation is `event.workflow == workflow` (`evaluator.py:184`). Nothing distinguishes `production` from `staging`/`dev`/`sandbox`/`canary`. A staging run that reuses or is assigned matching identifiers produces evidence that correlates to a production control. There is no `environment`, `deployment_id`, or `assurance_boundary` field to prevent it.
- **Customer/production impact:** A production control could be greened by staging evidence — unsupported green across environments. Because agents stamp this reference onto every emitted event, the boundary must be settled **before** Claude writes emission code (adding a required field later is a breaking change).
- **Minimal correction (Codex):** Add `environment: Identifier` (and optional `assurance_boundary`) to `WorkflowExecutionReference`; include it in equality/correlation. **Do not** add AWS-specific fields (no `region`/`account`) — keep it cloud-neutral per PROJECT_RULES.
- **Regression test:** `test_staging_environment_cannot_satisfy_production_control`.
- **Owner:** Codex schema; product-owner decides the environment taxonomy.

### H6 — Provenance granularity too coarse for agent-emitted evidence; one control-level provenance for heterogeneous requirements
- **Severity:** High (freeze before agent emission)
- **Location:** `models.py:92-98` (`Provenance` = prompt/model/policy/schema only), `models.py:144-157` (`ControlDefinition.expected_provenance` is single, control-level).
- **Failure scenario:** Recovery/currency is decided by `event.provenance == control.expected_provenance` (`evaluator.py:193`). A **guardrail regression** or an **MCP-tool/agent-version** change that keeps prompt/model/policy/schema constant is invisible — obsolete-provenance detection cannot fire, so a control can read GREEN after a silent guardrail downgrade. Also, different requirements of one control may originate from different agents/deterministic components with different version vectors, yet only one `expected_provenance` exists.
- **Customer/production impact:** False recovery / false green after an agent- or guardrail-layer change — undetectable by the assurance engine. This is squarely the agent-integration contract, so it is a Claude/Codex shared freeze item.
- **Minimal correction (shared):** Extend `Provenance` with optional `agent_version`, `tool_catalog_version`, `mcp_server_version`, `orchestration_version`, `guardrail_version`, `runtime_config_version`; define matching semantics (which fields must match for "current"). Allow per-`RequiredEvidenceSpecification` `expected_provenance` override. Keep new fields optional to preserve backward compatibility, but decide matching before agents emit.
- **Regression test:** `test_guardrail_version_change_marks_provenance_obsolete`.
- **Owner:** Shared (Codex schema; Claude defines what agents stamp; product-owner ratifies the version vector).

### H7 — Clock skew hard-rejects legitimate evidence at the envelope
- **Severity:** High
- **Location:** `models.py:178-182` (`ingested_at < observed_at` raises `ValidationError`).
- **Failure scenario (reproduced):** `observed_at = NOW`, `ingested_at = NOW − 1ms` (sub-millisecond skew between the observing agent and the ingesting service) → **`ValidationError`; the event is dropped entirely.**
- **Customer/production impact:** In any distributed deployment, normal clock skew silently discards real evidence → the control degrades to `REQUIRED_EVIDENCE_MISSING`/AMBER for no genuine reason, or ingestion errors. Latency/reliability harm with a false-uncertainty customer signal.
- **Minimal correction (Codex):** Replace the hard reject with a bounded tolerance (e.g., accept `ingested_at >= observed_at − skew_tolerance`, normalize `ingested_at = max(ingested_at, observed_at)`), or **quarantine** beyond tolerance as an AMBER reason rather than a construction failure. Make tolerance a policy field, not a magic constant.
- **Regression test:** `test_small_clock_skew_is_tolerated_not_dropped` and `test_gross_skew_is_quarantined_amber`.
- **Owner:** Codex.

### H8 — The "unsupported GREEN is impossible" property test is materially narrower than its claim
- **Severity:** High (test-coverage; the claim is currently overstated — B1 lives in the gap)
- **Location:** `tests/domain/test_evaluator.py:272-308`.
- **Failure scenario:** The state-space test fixes **one control, one requirement, `minimum_count=1`, one event**. It never exercises multiple requirements (where B1 hides), `minimum_count > 1`, source-event collisions, mixed current+obsolete cohorts, simultaneous RED+AMBER reduction, future-dated evidence, or remediation-boundary equality. The passing suite therefore does **not** substantiate the headline promise.
- **Customer/production impact:** A green test board misrepresents assurance coverage to the team and to the assessor — an internal "unsupported green."
- **Minimal correction (Codex), smallest meaningful expansion:**
  1. Two same-type requirements, one bound event → **AMBER** (locks B1).
  2. `minimum_count=2` with one passing event → **AMBER**.
  3. Remediation-boundary equality (`observed_at == verification_required_after`) → asserted, documented behavior (see M4).
  4. One RED requirement + one AMBER requirement on distinct controls → reduces to **RED**, both controls named.
  5. Future-dated evidence (`observed_at > now`) → AMBER, never GREEN.
- **Owner:** Codex.

### H9 — Declared runtime (3.13) was never the tested runtime (3.12.7)
- **Severity:** High (verification-integrity)
- **Location:** `pyproject.toml:9` (`requires-python = ">=3.13"`) vs verified interpreter Python 3.12.7.
- **Failure scenario:** The project claims a floor of 3.13 but 3.13 has not been run once. `typing.Self`/PEP 604 usage happens to work on 3.12, so the mismatch is currently latent — but any 3.13-only assumption, or a reviewer/assessor running 3.13, ships unverified. Equally, a fresh 3.13 machine cannot install pinned deps that were only proven on Anaconda 3.12.
- **Customer/production impact:** A false "verified on the declared runtime" claim; reproducibility gap on any clean machine.
- **Minimal correction (Codex/human):** Either (a) actually create and test under a 3.13 venv, or (b) lower `requires-python` to `>=3.12` to match what is verified. Do not document 3.13 as tested until it is.
- **Regression test:** CI matrix pinning the interpreter; until CI exists, record the exact tested version in the handbook (done — labeled 3.12.7).
- **Owner:** Codex config; product-owner decides target floor.

---

## 5. Medium / Low findings

### M1 — `attributes` dict is mutable despite `frozen=True`
- **Location:** `models.py:173`. **Reproduced:** `evidence.attributes["injected"] = {...}` succeeds after validation (top-level field rebind is correctly blocked). Risk: an accepted, already-hashed evidence payload can be mutated post-validation, breaking dedup identity (`_logical_payload`, `evaluator.py:341-346`) and the immutability guarantee. **Fix (Codex):** coerce to an immutable mapping at validation (e.g., store a `frozendict`-equivalent or a canonical JSON string, or `field_validator` deep-freezing). **Test:** `test_evidence_attributes_are_immutable`. **Owner:** Codex.

### M2 — Port test checks method *names* only, not signatures/return types
- **Location:** `tests/domain/test_ports.py:46-53`. `runtime_checkable` `isinstance` verifies attribute presence only; the fakes return `object()` and wrong types yet pass. **Fix (Codex):** add static conformance — typed variables `x: ports.EvidenceRepository = InMemoryEvidenceRepository()` with correctly typed fakes, so `mypy` enforces signatures. **Test:** the typed assignments themselves (mypy-checked). **Owner:** Codex.

### M3 — Dedup identity key is not scoped to tenant/environment/workflow
- **Location:** `evaluator.py:293-295` keys dedup on `(source, source_event_id)`. Safe only while callers scope evidence to one execution. A shared connector reusing `source_event_id` across tenants/environments, or cross-boundary evidence in one call, could collide and manufacture spurious `EVIDENCE_CONFLICT` AMBER. **Fix (Codex):** key on `(tenant, environment, workflow, source, source_event_id)` once H5 lands, or assert single-boundary input. **Test:** `test_same_source_event_id_across_tenants_does_not_collide`. **Owner:** Codex.

### M4 — Remediation-boundary equality is strict `>` and undocumented
- **Location:** `evaluator.py:202-214`. **Reproduced:** evidence observed *exactly at* `verification_required_after` → AMBER/`REMEDIATION_UNVERIFIED`. Defensible (recovery must be strictly after remediation) but unstated; a one-second-resolution clock could bite. **Fix (shared decision):** document the boundary semantics explicitly and add the equality test from H8. **Owner:** product-owner ratifies; Codex documents.

### M5 — Repository hygiene / reproducibility (no removals performed)
- **Location:** repo root. No `.gitignore`; `.DS_Store`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` untracked; no project-local venv; no lockfile; `mypy`/`ruff`/`hypothesis` undeclared in `pyproject.toml`; no lint configured; **no baseline commit**. **Minimal correction plan (Codex/human, in order):** (1) add `.gitignore` for `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.DS_Store`, `.venv/`; (2) declare `mypy`, `ruff` (and choose whether `hypothesis` is used) under `[project.optional-dependencies]`; (3) create a project-local venv + lockfile; (4) make the **first commit** so future diffs are reviewable. **Owner:** Codex config; product-owner authorizes the commit.

### M6 — No data-lane / evidence-origin classification for generalization (planned)
- **Location:** contracts (absent by design at this stage). Future agent/eval contracts must distinguish deterministic-synthetic-canary, diverse-synthetic-dev, licensed-real, locked blind-holdout, adversarial/OOD, and consented-shadow data, so synthetic-only accuracy is never presented as general production accuracy. **Fix (shared, later):** add an `evidence_origin`/`data_classification` enum on the eval record (not necessarily on live evidence). **Owner:** shared/product-owner. Do not build datasets now.

### L1 — Reason-code display priority is coupled to enum declaration order
- **Location:** `evaluator.py:25` (`_REASON_ORDER = enumerate(ReasonCode)`). Reordering the enum silently reorders customer-facing reason priority. **Fix:** an explicit priority map. **Owner:** Codex.

### L2 — Customer summary prints the `control_id` slug, not `display_name`
- **Location:** `evaluator.py:408`. Customer sees `pii-redaction`, not "PII Redaction." Minor readability; relevant to Claude-owned customer explanations. **Owner:** shared/Claude.

### L3 — Future-dated evidence is reported as `EVIDENCE_CONFLICT`
- **Location:** `evaluator.py:216-222`. Correctly prevented from GREEN, but a distinct "future/clock" reason would explain it better and pairs with H7. **Owner:** Codex.

### L4 — Several contracts are unexercised by any test
- `IncidentRecord`, `NotificationPort`, `EventPublisher`, `IdentityContext`/`IdentityPrincipal` have no behavioral test. Acceptable for contract-first scaffolding, but they carry the invariant gaps in H2–H4. **Owner:** Codex (add once invariants land).

---

## 6. Acceptance-criterion audit (plan §Global Constraints)

| Criterion (plan) | Status | Evidence |
|---|---|---|
| UTC-aware, immutable, extra-forbidden contracts | **Mostly met** | `_require_utc`, `extra="forbid"`, `frozen=True` — but nested `attributes` dict is mutable (M1) |
| Missing/stale/inconsistent/incomplete/unavailable/uncorrelated ⇒ never GREEN | **Met for single requirement; BROKEN for multi-requirement** | B1 reproduced GREEN |
| Explicit current failure ⇒ RED | **Met** | `test_explicit_failed_outcome_is_red` + reproduced |
| Recovery requires current-provenance evidence after remediation | **Met for prompt/model/policy/schema; blind to agent/tool/guardrail versions** | H6 |
| Reason codes + customer next-safe-action on every result | **Met** | `StateTransitionExplanation` populated; slug vs display-name nit (L2) |
| No AWS/agent/MCP/LLM/network in core | **Met** | import-leak scan clean |
| Deterministic final state | **Met** | pure over injected clock; sorted reductions |
| Duplicate source events cannot change result | **Met** | `test_duplicate_source_event_does_not_alter_the_result` |
| Event-time (not ingestion-order) evaluation | **Met** | `test_out_of_order_delivery_uses_event_time_not_input_order` |

Net: the deterministic engine and cloud-neutrality criteria are genuinely satisfied; the **"never unsupported GREEN"** criterion is **not** (B1), and two recovery/safety promises are only partially enforced at the contract layer (H3, H4, H6).

---

## 7. Missing regression tests (consolidated)

1. `test_two_same_type_requirements_need_two_bound_events` (B1) — highest priority.
2. `test_minimum_count_greater_than_one_requires_enough_events` (H8).
3. `test_accepted_outcomes_is_honored_or_rejected` (H1).
4. `test_assurance_evaluation_status_matches_explanation` / `test_green_explanation_forbids_failure_reasons` (H2).
5. `test_resolved_incident_requires_resolution_evidence` (H3).
6. `test_passing_canary_requires_confirmed_no_side_effects` (H4).
7. `test_staging_environment_cannot_satisfy_production_control` (H5).
8. `test_guardrail_version_change_marks_provenance_obsolete` (H6).
9. `test_small_clock_skew_is_tolerated_not_dropped` / `test_gross_skew_is_quarantined_amber` (H7).
10. `test_simultaneous_red_and_amber_reduces_to_red` and `test_future_dated_evidence_is_never_green` (H8).
11. `test_remediation_boundary_equality_behavior` (M4).
12. `test_evidence_attributes_are_immutable` (M1).
13. Typed port-conformance assignments checked by mypy (M2).

---

## 8. Minimal correction sequence (do in this order)

1. **B1** — add requirement↔evidence binding (schema + evaluator) and its test. *Unblocks the product promise.*
2. **H5, H6** — freeze `WorkflowExecutionReference` (`environment`) and `Provenance` (agent/tool/guardrail versions + per-requirement override). *These are the contracts agents emit; freeze before Claude writes emission code.*
3. **H2, H3, H4** — add the three cross-field invariants + tests. *Cheap, high customer-safety value.*
4. **H1** — resolve the `accepted_outcomes` contradiction.
5. **H7, M1, M3** — skew tolerance, immutable attributes, scoped dedup key.
6. **H8** — expand the property test to the five dimensions.
7. **H9, M5** — fix runtime declaration; add `.gitignore`, declare tool deps, venv/lockfile, first commit.
8. **M4, M6, L1–L4** — documentation + hardening.

Steps 1–2 are the freeze gate for agent evidence emission. Steps 3–8 can proceed in parallel with the isolated agent prototype.

## 9. Safe / unsafe scope for the next implementation

**Claude MAY create now (strictly isolated — no dependency on disputed contracts B1/H5/H6):**
- `src/proofloop/agents/model_provider.py` — the `ModelProvider` abstraction + a deterministic fake/echo provider (no network).
- `src/proofloop/agents/extraction_agent.py` and `.../reconciliation_agent.py` — **business logic only**, returning their **own** typed result models (extracted fields; reconciliation decision), **not** `EvidenceEnvelope`.
- `src/proofloop/agents/prompts/*` — prompt templates.
- `src/proofloop/agents/mcp/tool_specs.py` — MCP tool **signatures/schemas** for business actions (no evidence emission).
- Their unit tests under `tests/agents/`.

**Claude MUST NOT create yet (binds to disputed contracts):**
- Any code constructing `EvidenceEnvelope`, `Provenance`, or `WorkflowExecutionReference` (evidence-emission adapter) — blocked by B1, H5, H6.
- Guardrail middleware that emits control-execution evidence — same reason.
- Customer-facing explanation code that consumes `AssuranceEvaluation` — wait for H2 invariants so the LLM cannot be handed a contradictory object.

**Codex owns all fixes in §8.** One owner per file; no cross-edits without a product-owner handoff.

## 10. Human product-owner decisions required

1. **Environment taxonomy (H5):** what are the legal `environment` values, and is `assurance_boundary` needed for canaries?
2. **Provenance vector (H6):** which version fields are mandatory for "current," and do you want per-requirement provenance overrides?
3. **`accepted_outcomes` (H1):** delete it (PASS-only) or genuinely support it with reachability validation?
4. **Runtime floor (H9):** target Python 3.13 (and actually test it) or drop to `>=3.12`?
5. **Git baseline (M5):** authorize the first commit + `.gitignore` (currently forbidden until you say so).
6. **Skew tolerance (H7):** acceptable clock-skew window and quarantine-vs-reject policy.

## 11. Five files the human should inspect

1. `src/proofloop/domain/evaluator.py` — lines 159-168 (B1 binding) and 243-289 (outcome/`accepted_outcomes` logic, H1).
2. `src/proofloop/domain/models.py` — `EvidenceEnvelope` 160-183 (B1, H7, M1), `WorkflowExecutionReference` 101-107 (H5), `Provenance` 92-98 (H6).
3. `src/proofloop/domain/models.py` — `IncidentRecord` 209-221 & `CanaryResult` 236-255 (H3, H4).
4. `tests/domain/test_evaluator.py` — 272-308 (the over-claimed property test, H8).
5. `pyproject.toml` — line 9 runtime mismatch + missing tool deps (H9, M5).

## 12. Concepts the human must understand

- **Evidence↔requirement binding:** why a control with two obligations needs two *bound* proofs, not two matches of one event (B1).
- **Contract vs behavior:** the evaluator is correct today, but the *models* permit unsafe objects other code will build (H2–H4). Invariants belong on the model, not only in the evaluator.
- **Provenance as a version vector:** "current evidence" means "same versions," and that must include the agent/guardrail/tool layer, or regressions there are invisible (H6).
- **Deterministic vs probabilistic assurance:** the LLM may polish prose but must never set status/reason/action — the structured fields exist precisely to fence it out (keep this true when Claude adds explanations).
- **Verified vs declared:** 3.13 declared ≠ 3.13 tested; synthetic pass ≠ general accuracy (H9, M6).

## 13. Commands the human should run

```bash
cd "/Users/srisruthi/Aivar Project"
/opt/anaconda3/bin/python3 --version          # see the ACTUAL runtime (3.12.7)
/opt/anaconda3/bin/python3 -m pytest -q         # 23 passed
/opt/anaconda3/bin/python3 -m mypy src/proofloop
/opt/anaconda3/bin/python3 -m compileall -q src tests
grep -rniE "boto3|aws|langchain|openai|mcp|bedrock|httpx|socket" src/proofloop/  # expect none
```

## 14. Likely interview questions (and where the answer lives)

- "How do you *guarantee* you never show green without evidence?" → today you cannot for multi-requirement controls (B1); the honest answer is the binding fix + the expanded property test.
- "What stops staging data from greening production?" → currently nothing (H5); name the `environment` correlation fix.
- "If someone downgrades a guardrail, does your green change?" → not yet (H6); explain the provenance vector.
- "Why deterministic, not an LLM judge?" → identical prompts flip LLM verdicts; assurance must be reproducible and auditable — the LLM only polishes prose over immutable structured fields.
- "How do you handle duplicate / out-of-order / clock-skewed events?" → dedup by source-event identity, evaluate by event time (both tested); skew currently over-rejects (H7) — a known limitation with a bounded-tolerance fix.

## 15. Final decision

**CONDITIONAL GO.**

Codex must land **B1** (evidence↔requirement binding) and freeze **H5** (environment) and **H6** (provenance vector) before **any** Claude evidence-emission, guardrail-evidence, or customer-explanation code is written. In parallel, Claude may build the strictly isolated agent scope enumerated in §9 (model provider, agent business logic, prompts, MCP tool signatures, and their tests) because none of it depends on the disputed contracts. High findings H1–H4, H7–H9 and the Medium/Low items should be cleared before integration/deployment, not before the isolated prototype.

This is not a GO-on-green-tests: the passing suite does not cover the dimension where the product's core promise breaks.

---

*Reviewer note: no Codex source or tests were modified; no files were deleted; no commit/push/deploy/install occurred. All findings above were reproduced by executing the code on 2026-07-18 under Python 3.12.7.*
