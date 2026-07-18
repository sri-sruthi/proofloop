# ProofLoop Track E2 Release-Blocker Repairs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the authorized Codex-owned local release blockers without changing agent behavior, cloud state, or Git state.

**Architecture:** Preserve the composition root's branch-local closures through typed named functions, preserve the serialized PASS contract through a line-level Bandit suppression, and prove pytest 9 compatibility in a disposable environment before updating dependency policy. Release documents will record only freshly executed evidence.

**Tech Stack:** Python 3.12, Pydantic 2, pytest 9, mypy, Ruff, Bandit, pip-audit, SAM template validator, Node syntax checks, Poppler/ReportLab if PDF regeneration is required.

## Global Constraints

- Do not edit Claude-owned files under `src/proofloop/agents/**`.
- Do not implement Claude observations O1/O2 or a caller run key.
- Do not deploy, invoke Bedrock, create cloud/GitHub resources, or mutate Git.
- AWS is active and Lambda is accessible in `ap-south-1`; no other AWS result may be inferred.

---

### Task 1: Named provider factories

**Files:**
- Modify: `tests/integration/test_agent_composition.py`
- Modify: `src/proofloop/infrastructure/composition.py`

**Interfaces:**
- Consumes: `InvoiceRunRequest`, `ModelProvider`, captured model/client/config values.
- Produces: `fake_provider_factory` and `bedrock_provider_factory` callables selected through `provider_factory`.

- [ ] Add assertions that the selected factories have stable names while retaining the existing two-instance Bedrock assertion.
- [ ] Run the focused tests and confirm failure on the current lambda name.
- [ ] Replace only the two assigned lambdas with typed nested functions.
- [ ] Re-run the focused tests and Ruff on the composition file.

### Task 2: Narrow Bandit suppression

**Files:**
- Modify: `src/proofloop/domain/models.py`
- Test: `tests/domain/test_contracts.py`

**Interfaces:**
- Consumes and preserves: `EvidenceOutcome.PASS`.
- Produces: the same public serialized value, with a line-level `B105` suppression.

- [ ] Confirm the existing contract test surface exercises `EvidenceOutcome.PASS` serialization.
- [ ] Add the explanatory inline `# nosec B105` annotation without changing the enum value.
- [ ] Run the domain contract tests and Bandit against `models.py`.

### Task 3: Pytest 9 compatibility and dependency policy

**Files:**
- Modify only after validation: `pyproject.toml`

**Interfaces:**
- Consumes: current Python `>=3.12,<3.14` project and development tool constraints.
- Produces: `pytest>=9.0.3,<10` if and only if the clean gate is compatible.

- [ ] Create a disposable virtual environment outside the repository.
- [ ] Install the editable project, pytest 9, mypy, Ruff, Bandit, and pip-audit.
- [ ] Run pytest, mypy, Ruff, Bandit, strict audit, compilation, demos, template validation, dashboard syntax, and isolation scans.
- [ ] If compatible, update `pyproject.toml`; otherwise retain it and record the exact incompatibility.
- [ ] Reinstall from the updated declared dependency and repeat the complete gate.

### Task 4: Release evidence and submission status

**Files:**
- Modify: `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`
- Modify: relevant Markdown sources in `docs/submission/**`
- Regenerate: `docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.pdf` only if its status text is stale.

**Interfaces:**
- Consumes: exact command outputs from Tasks 1-3 and current AWS authorization facts.
- Produces: an auditable blocker ledger and consolidated next release-gate prompt.

- [ ] Classify Codex-owned blockers as closed only from fresh zero-exit evidence.
- [ ] Report any remaining Claude-owned finding without editing it.
- [ ] Replace stale AWS-payment wording with the authorized Mumbai Lambda fact while retaining all unexecuted-result disclaimers.
- [ ] If the PDF changes, regenerate, render every page, and visually inspect it.
- [ ] Run placeholder, secret-pattern, whitespace, ownership, and final full-gate checks.
- [ ] Report exact commands/results, remaining blockers, five inspection files, and the next consolidated prompt.

