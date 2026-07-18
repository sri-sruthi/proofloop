# ProofLoop Track F2 Private Git, CI, Python 3.13, and SAM Gate Plan

> **For Codex:** Execute this plan in the canonical repository without creating AWS resources, deploying, invoking Bedrock, publishing publicly, or creating the final submission ZIP.

**Goal:** Establish a privacy-verified private Git baseline, run the release candidate through GitHub Actions on Python 3.12 and 3.13 with SAM validation/build, reproduce the target-runtime and SAM gate locally where practical, and record an evidence-backed predeployment verdict.

**Architecture:** Treat the current uncommitted tree as the proposed root commit. Tighten repository hygiene and CI verification before staging, inspect every proposed path and binary, and block remote use unless GitHub reports `PRIVATE` and `private: true`. Gate the root commit in CI, then commit evidence-only handoffs separately so the release-code SHA and its CI run remain stable and auditable.

**Tech Stack:** Git/GitHub CLI, GitHub Actions, Python 3.12/3.13, pytest, mypy, Ruff, Bandit, pip-audit, AWS SAM CLI, Docker-compatible SAM build, Node.js dashboard syntax checking.

---

### Task 1: Freeze scope and strengthen hygiene/CI declarations

**Files:**
- Modify: `.gitignore`
- Modify: `.github/workflows/ci.yml`
- Verify: `.env.example`

1. Add narrow ignore rules for virtual environments, Python/Node/test/build caches, SAM artifacts, OS metadata, temporary renders, credential files, and environment-specific secrets while retaining `.env.example`.
2. Add an explicit dashboard JavaScript syntax check to CI and compile `src`, `tests`, `scripts`, and `infra/scripts`.
3. Keep CI read-only and deployment-free; do not add AWS credentials or deployment steps.

### Task 2: Build and inspect the proposed root-commit manifest

**Files:**
- Inspect: every non-ignored repository path
- Write evidence later: `codex/handovers/FINAL_CI_AND_SAM_GATE.md`

1. Enumerate every proposed file, grouped by top-level path, with file count and size.
2. Inspect unusually large files and all binary artifacts; extract PDF text/metadata and visually verify screenshots where applicable.
3. Scan text and printable binary content for AWS key patterns, private-key headers, API/token assignments, credential dumps, customer/invoice data, captured prompts/model output, environment dumps, and unexpectedly large artifacts.
4. Distinguish required prompt source and explicitly synthetic fixtures from captured runtime/customer content.
5. Stop before commit if any secret, customer data, captured prompt/model output, or unexplained binary remains.

### Task 3: Run the complete pre-commit local gate

**Files:**
- Verify: `src/**`, `tests/**`, `scripts/**`, `infra/**`, `dashboard/**`

1. Create a disposable environment from the declared dependency policy.
2. Run pytest, mypy, Ruff, Bandit, strict dependency audit, pip integrity, compileall, both demos, structural template validation, Lambda source imports, dashboard syntax, import-isolation scans, dangerous-code scans, and privacy/secret scans.
3. Run Python 3.13 and SAM locally if tooling is available or can be installed safely; record exact limitations rather than inferring success.

### Task 4: Stage and inspect the exact root commit

**Files:**
- Inspect: `git status`, staged manifest, staged diff, binary list

1. Stage only the reviewed non-ignored tree.
2. Review `git diff --cached --stat`, `--name-status`, `--check`, and the complete textual diff.
3. Re-run credential/privacy patterns against the staged blob set.
4. Present a concise proposed-file manifest before creating the commit.

### Task 5: Create and prove the strictly private GitHub remote

**Remote:** `sri-sruthi/proofloop-aivar-private` unless safely unavailable

1. Confirm the target name is not an unrelated existing repository.
2. Create an empty GitHub repository with private visibility only.
3. Query both `gh repo view` and the GitHub repository API; require `visibility: PRIVATE`, `isPrivate: true`, and `private: true` before adding or pushing the remote.
4. Stop without pushing if any privacy field is absent, ambiguous, or false.

### Task 6: Create and push the root baseline commit

**Files:**
- Commit: the fully reviewed staged tree

1. Confirm repository-local Git identity without exposing personal credentials.
2. Create one intentional root commit without rewriting or deleting user work.
3. Add only the conclusively private remote and push `main`.
4. Record the root commit SHA and remote visibility evidence.

### Task 7: Inspect and, if necessary, repair GitHub Actions

**Files:**
- Diagnose first: `.github/workflows/ci.yml`, job logs
- Modify only Codex-owned files if a verified defect requires repair

1. Locate the workflow run for the root commit and inspect actual step/job logs for Python 3.12 and 3.13.
2. Verify pytest, mypy, Ruff, Bandit, pip-audit, compilation/imports, dashboard syntax, SAM validation/build, and built-handler imports.
3. On failure, invoke the CI-debugging and systematic-debugging workflows, determine root cause, and use TDD for behavioral fixes.
4. Do not edit Claude-owned agent/privacy files; write a precise handoff if failure belongs there.
5. Re-run every affected gate and require a green final workflow before closing CI/SAM blockers.

### Task 8: Record the final CI/SAM gate

**Files:**
- Create: `codex/handovers/FINAL_CI_AND_SAM_GATE.md`
- Modify: `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`

1. Record exact local and CI commands/results, Python 3.13 evidence, SAM validate/build and built-handler evidence, private remote proof, release-code SHA, CI URLs/job conclusions, closed blockers, and remaining AWS/deployment blockers.
2. State explicitly that no AWS resource, deployment, CloudFormation execution, real-model request, or final ZIP was created.
3. Commit and push the evidence-only handoff to the same verified private remote, then verify its CI run as a documentation-only descendant of the gated release-code commit.
4. Conclude only whether it is safe to prepare a separately reviewed CloudFormation change set; do not claim production readiness.
