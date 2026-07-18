# ProofLoop Contracts-First Foundation Implementation Plan

> **For agentic workers:** Implement inline with test-driven development. The product owner explicitly forbids commits, pushes, deployments, and billable resources during this task.

**Goal:** Build the smallest cloud-neutral ProofLoop domain foundation with typed contracts, dependency ports, and a deterministic evidence evaluator.

**Architecture:** External and domain data is validated with immutable Pydantic models. Infrastructure is represented only by Python `Protocol` ports. A pure evaluator receives controls, evidence, a workflow execution reference, and an injectable clock; it returns an explainable assurance result without importing AWS or invoking an LLM.

**Tech Stack:** Python 3.13-compatible syntax, Pydantic v2, Python protocols, pytest.

## Global Constraints

- Preserve all existing user files and do not edit `claude/`.
- Do not add AWS SDKs, agent frameworks, MCP libraries, LLM clients, or network calls.
- Use UTC-aware timestamps and immutable, extra-forbidden domain contracts.
- Missing, stale, inconsistent, incomplete, unavailable, or uncorrelated evidence can never produce GREEN.
- Explicit current evidence of required-control failure produces RED.
- Recovery requires current-provenance evidence observed after the remediation/version-change time.
- Every evaluator result includes machine-readable reason codes and a customer-readable next safe action.
- Do not commit, push, deploy, or create billable resources.

---

### Task 1: Canonical rules and Python test harness

**Files:**
- Create: `docs/PROJECT_RULES.md`
- Create: `pyproject.toml`
- Create: `src/proofloop/__init__.py`
- Create: `src/proofloop/domain/__init__.py`

**Produces:** A single source of truth and an importable `src/` package with pytest configured to find it.

- [ ] Write the canonical product, customer, ownership, verification, and handoff rules.
- [ ] Configure Python `>=3.13`, Pydantic v2, and pytest without infrastructure dependencies.
- [ ] Verify collection initially reports no tests rather than an import/configuration error.

### Task 2: Typed domain contracts

**Files:**
- Create: `tests/domain/test_contracts.py`
- Create: `src/proofloop/domain/models.py`

**Interfaces:**
- Produces: `ControlDefinition`, `RequiredEvidenceSpecification`, `EvidenceEnvelope`, `EvidenceOutcome`, `EvidenceFreshnessPolicy`, `WorkflowExecutionReference`, `AssuranceStatus`, `StateTransitionExplanation`, `IncidentRecord`, `CanaryDefinition`, `CanaryResult`, `Provenance`, `AssuranceEvaluation`, and supporting enums.

- [ ] Write failing tests for UTC enforcement, invalid freshness windows, forbidden unknown fields, safe canary modes, and immutable contracts.
- [ ] Run `python3 -m pytest tests/domain/test_contracts.py -q` and verify failure because the contracts do not exist.
- [ ] Implement the minimum Pydantic contracts and validation.
- [ ] Re-run the contract tests and verify they pass.

### Task 3: Cloud-neutral ports

**Files:**
- Create: `tests/domain/test_ports.py`
- Create: `src/proofloop/domain/ports.py`

**Interfaces:**
- Produces: `EvidenceRepository`, `ControlRepository`, `EventPublisher`, `CanaryExecutor`, `NotificationPort`, `Clock`, and `IdentityContext` protocols.
- Consumes: Typed contracts from `proofloop.domain.models` only.

- [ ] Write failing structural-conformance tests using small in-memory fakes.
- [ ] Run `python3 -m pytest tests/domain/test_ports.py -q` and verify failure because the protocols do not exist.
- [ ] Implement runtime-checkable protocols with explicit method signatures.
- [ ] Re-run the port tests and verify they pass.

### Task 4: Deterministic assurance evaluator

**Files:**
- Create: `tests/domain/test_evaluator.py`
- Create: `src/proofloop/domain/evaluator.py`

**Interfaces:**
- Produces: `evaluate_assurance(*, controls, evidence, workflow, clock, previous_status=None) -> AssuranceEvaluation`.
- Consumes: Contract models plus the `Clock` protocol.

- [ ] Write failing tests for GREEN, missing/stale/conflicting/unavailable evidence, explicit failure, wrong execution, obsolete provenance, remediation recovery, duplicates, out-of-order delivery, and customer explanations.
- [ ] Run `python3 -m pytest tests/domain/test_evaluator.py -q` and verify failure because the evaluator does not exist.
- [ ] Implement exact-workflow filtering, source-event deduplication, event-time ordering, provenance/freshness/recovery checks, deterministic reduction, reason codes, and explanations.
- [ ] Re-run evaluator tests and verify they pass.

### Task 5: Property coverage and final verification

**Files:**
- Modify: `tests/domain/test_evaluator.py`
- Modify only if needed: `src/proofloop/domain/evaluator.py`

**Produces:** Exhaustive covered-state evidence that unsupported GREEN is impossible.

- [ ] Add a parameterized state-space test covering outcome, presence, freshness, correlation, and provenance combinations.
- [ ] Run the new property test first and verify it exposes any unsupported-GREEN path.
- [ ] Make the smallest evaluator correction if needed and re-run the full suite.
- [ ] Run `python3 -m pytest -q`, `python3 -m compileall -q src tests`, dependency/import leak searches, and `git diff --check`.
- [ ] Review `git diff`, map every acceptance criterion to a test or artifact, and prepare the required handoff without committing.
