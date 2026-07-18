# ProofLoop Track D2 Release-Candidate Implementation Plan

> **For agentic workers:** Execute inline in this session. Do not delegate or
> mutate implementation/Git because Claude is independently auditing the shared
> tree and the product owner restricted ownership to documentation.

**Goal:** Run the complete local release-candidate gate and deliver a verified,
professionally rendered PS-6.2 submission package.

**Architecture:** Treat the current tree as immutable input. Collect command and
manual evidence first, then derive each submission artifact from the same result
matrix. Generate the PDF last and inspect every rendered page before the final
handoff.

**Tech Stack:** Python 3.12, pytest, mypy, Ruff, Bandit, pip-audit, SAM when
available, WSGI, static HTML/CSS/JavaScript, ReportLab, Poppler.

## Global Constraints

- Modify only `docs/**` and `codex/**`.
- Do not deploy, invoke AWS/Bedrock, create resources, install global software,
  mutate Git/GitHub, or expose secrets/PII/prompts/reasoning.
- Do not edit implementation to repair a QA finding.
- Use synthetic reserved data only.
- Report unavailable commands honestly.

---

### Task 1: Source and environment inventory

**Files:**
- Read: all ten sources named by the Track D2 brief
- Create: `docs/submission/MANUAL_QA_EVIDENCE.md` after evidence exists

- [ ] Record `python --version`, `node --version`, installed check tools, SAM,
  Poppler, and PDF-library availability.
- [ ] Inspect current branch/log/status, ignored build/cache artifacts, tracked
  secret-shaped filenames, and Claude review timestamps without Git mutation.
- [ ] Record the exact original PS-6.2 wording and distinguish assignment
  expectations from locally verified capabilities.

### Task 2: Isolated release gate

**Files:** read-only project tree; disposable environment under `/tmp`.

- [ ] Create `/tmp/proofloop-d2-venv` and install the project plus declared dev
  extras there if dependencies are locally/network available without global
  changes.
- [ ] Run full pytest, mypy, Ruff, Bandit, pip-audit, compileall, both demos,
  template validator, dashboard syntax, Lambda source imports, isolation scans,
  secret/dangerous-code scans, and repository-hygiene checks.
- [ ] If SAM exists, run `sam validate` and `sam build --use-container`, then
  verify both handlers from the build artifacts. Otherwise record all three as
  unavailable.
- [ ] Preserve exact counts, versions, exit codes, and honest warnings for the
  evidence ledger.

### Task 3: Manual API and dashboard QA

**Files:**
- Create: `docs/submission/evidence/*.png` only for customer-safe UI states
- Modify: `docs/submission/MANUAL_QA_EVIDENCE.md`

- [ ] Start the real local WSGI API with `PROOFLOOP_MODEL_PROVIDER=fake` and an
  ephemeral API key that is never printed or captured.
- [ ] Exercise authenticated GREEN, missing/wrong auth, invalid/oversized input,
  and poisoned-input privacy through HTTP.
- [ ] Exercise malformed output, model/tool timeout, duplicate/HITL, exact
  replay, conflict, canary RED, remediation AMBER, and fresh-proof GREEN through
  deterministic integration fixtures using the same public contracts.
- [ ] Serve the real dashboard, inspect compliance/timeline/incident rendering,
  capture useful customer-safe screenshots, and inspect responses/logs for all
  forbidden values.
- [ ] Stop local processes and record each of the fourteen scenario verdicts.

### Task 4: Submission Markdown artifacts

**Files:**
- Create: `docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.md`
- Create: `docs/submission/DEMO_RUNBOOK.md`
- Create: `docs/submission/MANUAL_QA_EVIDENCE.md`
- Create: `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`
- Create: `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`

- [ ] Write the final narrative from the assignment, source register, approved
  architecture, and fresh QA evidence, including all status labels and prohibited
  overclaims.
- [ ] Write a timed five-to-eight-minute demo with preflight, exact commands,
  expected output, alternate failure path, and privacy cautions.
- [ ] Write the post-activation checklist with every required human choice,
  build/deploy/smoke evidence, rollback/delete path, and ownership.
- [ ] Write the release handoff in the canonical project format, including Claude
  review ownership, exact blockers, next activation prompt, and five files.
- [ ] Scan all artifacts for placeholders, unverified claims, secrets, raw PII,
  malformed links, and inconsistent test counts.

### Task 5: Professional PDF

**Files:**
- Create: `docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.pdf`
- Temporary: `/tmp/proofloop-d2-pdf/**`

- [ ] Load the bundled document/PDF runtime and generate a styled ReportLab PDF
  using only verified content from the canonical Markdown and evidence ledger.
- [ ] Validate PDF metadata, page count, text extraction, required section terms,
  and absence of placeholders/secrets.
- [ ] Render every page with Poppler, inspect every PNG, and iterate until no
  clipping, overlap, broken glyph, unreadable table, or inconsistent header/
  footer remains.

### Task 6: Final release verification

**Files:** all five Markdown/handoff artifacts plus the final PDF.

- [ ] Rerun full pytest, mypy, compileall, demos, template validator, JavaScript
  syntax, source imports, and isolation/security scans after artifact generation.
- [ ] Verify all six required artifacts exist, are non-empty, contain the required
  topics, and contain no prohibited claim or secret-shaped value.
- [ ] Inspect Git status to prove only authorized documentation paths changed
  during Track D2 and report the repository's no-baseline state.
- [ ] Deliver the exact local verdict, manual-QA summary, artifacts, blockers,
  next post-activation prompt, and five inspection files without committing or
  deploying.
