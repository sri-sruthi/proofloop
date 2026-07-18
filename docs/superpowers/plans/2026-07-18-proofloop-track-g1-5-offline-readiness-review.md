# ProofLoop Track G1.5 Offline Readiness Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an evidence-backed, documentation-only AWS execution-readiness review and reconcile reviewer-facing release facts without changing infrastructure behavior or contacting AWS.

**Architecture:** Treat the passing F2 commit and CI logs as the immutable technical baseline. Classify each deployment gap into pre-change-set, pre-execution, or post-deployment work; compare bounded implementation options; and update only reviewer documentation plus the new Codex handoff. Keep infrastructure, agent, privacy, AWS account, and Bedrock state untouched.

**Tech Stack:** Markdown, existing ProofLoop Python/SAM repository, Git diff and text verification.

## Global Constraints

- Do not call AWS, create or execute a change set, create resources, deploy, or invoke Bedrock.
- Do not edit `infra/template.yaml`, infrastructure implementation, or agent/privacy behavior.
- Do not add hosted-dashboard, alarm, identity, or secret-management services in G1.5.
- Preserve the F2 evidence: local Python 3.13, SAM validation/build, private GitHub, and Python 3.12/3.13 CI pass; AWS deployment and real Bedrock remain incomplete.
- Keep API-key authentication classified as a controlled development/demo boundary, not production identity.
- Recommend infrastructure implementation only for a separately approved Track G1.6; keep G2 limited to read-only AWS preflight and a non-executed change set after G1.6 passes CI.
- Do not commit or push unless the product owner separately requests it for G1.5.

---

### Task 1: Write the offline execution-readiness handoff

**Files:**
- Create: `codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md`

**Interfaces:**
- Consumes: F2 handoffs, `infra/template.yaml`, application CORS/auth behavior, the deployment checklist, and current official public AWS documentation.
- Produces: blocker classifications, implementation options, resource/cost inventory, product-owner decisions, recommended G1.6 design, and separate G1.6/G2 prompts.

- [ ] **Step 1: Record immutable facts and scope**

Document that G1.5 is offline and documentation-only; list the exact F2 commit/run evidence carried forward; state that no AWS/deployment/Bedrock evidence exists.

- [ ] **Step 2: Classify findings by release gate**

Classify allowed-origin injection, schedule activation, alarms, dashboard hosting, API-key boundary, data deletion/replacement, region/stack identity, costs, and human decisions as must-fix-before-final-change-set, must-fix-before-execution, or safe post-deployment work.

- [ ] **Step 3: Compare bounded options**

For each accepted blocker, provide 2-3 options with implementation scope, cost impact, failure risk, and a recommendation. Compare local dashboard, privately controlled hosted dashboard, and no hosting before backend smoke.

- [ ] **Step 4: Specify the recommended G1.6 design**

Recommend explicit `AllowedOrigin`, an explicit schedule-activation parameter disabled by default, and a minimal infrastructure-as-code alarm set whose thresholds/actions remain product-owner inputs. Separate essential development alarms from production-scale extensions.

- [ ] **Step 5: Add exact cost and ownership decisions**

List explicit and SAM-generated resources and the operations that incur charges. Do not invent a dollar total without approved traffic, model, region, retention, and alarm inputs. Add the compact product-owner decision table.

- [ ] **Step 6: Add separate next prompts**

Write one prompt for TDD-only G1.6 infrastructure hardening and one later prompt for G2 AWS read-only preflight plus a non-executed change set. State that G2 cannot begin until G1.6 is reviewed, implemented, and green in private CI.

### Task 2: Reconcile the README release facts

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: final F2 evidence and G1.5 blocker classification.
- Produces: a reviewer-facing status that distinguishes completed Python/SAM/private CI evidence from unexecuted AWS/Bedrock work.

- [ ] **Step 1: Correct stale status statements**

Replace Python 3.12-only/local-Python-3.13-unavailable wording with the exact F2 local and CI facts.

- [ ] **Step 2: Correct verification and deployment boundaries**

State that local native SAM and native ARM64 Linux CI packaging passed; local Docker was not claimed; no AWS deployment or real model call occurred.

- [ ] **Step 3: Add concise execution blockers**

State that explicit allowed origin, disabled-first schedule activation, operational alarms, and required product-owner decisions precede the final change set/execution.

### Task 3: Put the working demo first and reconcile the runbook

**Files:**
- Modify: `docs/submission/DEMO_RUNBOOK.md`

**Interfaces:**
- Consumes: deterministic foundation demo and F2 release evidence.
- Produces: a 30-45 second working demo at the start, followed by setup and the optional extended demo.

- [ ] **Step 1: Add the opening 30-45 second demo**

Place `python scripts/demo_proofloop.py` and a short narration immediately after document status. Make it the first recorded scene and preserve `GREEN -> AMBER -> RED -> AMBER -> GREEN`.

- [ ] **Step 2: Reframe setup as off-camera preparation**

Keep synthetic-data/key/privacy safeguards and local setup intact, but position them as preparation before recording rather than the opening scene.

- [ ] **Step 3: Reconcile the release verdict**

State that Python 3.13, SAM packaging, private GitHub and CI are complete; AWS deployment, alarms/change-set execution, and real Bedrock are not.

### Task 4: Reconcile the deployment and rollback checklist

**Files:**
- Modify: `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`

**Interfaces:**
- Consumes: F2 evidence and the G1.5 blocker taxonomy.
- Produces: checked completed gates, explicit pre-change-set/pre-execution blockers, and unchanged deployment/smoke/rollback controls.

- [ ] **Step 1: Update header and completed prerequisites**

Mark the private baseline, local Python 3.13, SAM validation/build, built-handler imports, and both CI jobs as complete with handoff/run references.

- [ ] **Step 2: Add the G1.5 accepted blockers**

Record missing origin injection, missing alarms, and currently enabled schedule as blockers. Add the local-vs-hosted dashboard and API-key-boundary decisions.

- [ ] **Step 3: Separate final-change-set and execution gates**

Require the reviewed G1.6 template and green private CI before creating the final non-executed change set; require identity/model/ARN/budget/owners/smoke/rollback decisions before execution.

- [ ] **Step 4: Preserve post-deploy checks**

Keep deployment, smoke, alarm, privacy and rollback boxes unchecked and do not imply any AWS result.

### Task 5: Verify scope, consistency, and carried-forward evidence

**Files:**
- Verify: all changed files
- Prove unchanged: `infra/template.yaml`, `infra/**`, `src/proofloop/**`, `tests/**`

**Interfaces:**
- Consumes: completed documentation edits.
- Produces: exact diff, scope proof, current test evidence, and a clean documentation consistency report.

- [ ] **Step 1: Check the diff scope**

Run `git status --short`, `git diff --check`, `git diff --name-only`, and `git diff -- infra src tests`.

Expected: only the plan, three reviewer documents and new Codex handoff differ; the infrastructure/source/test diff is empty.

- [ ] **Step 2: Scan for stale release claims and placeholders**

Run focused `rg` checks for stale Python 3.13/SAM/CI claims, `TBD`, `TODO`, production-ready claims, and combined G1.6/G2 authority. Resolve every unintended match.

- [ ] **Step 3: Run the regression and structural gates**

Run `python -m pytest -q`, `python infra/scripts/validate_template.py`, and `node --check dashboard/app.js`.

Expected: 266 tests pass, SAM package guardrails pass, and dashboard syntax exits zero. Verify the carried-forward private CI code-gate evidence remains run `29640732187` at commit `41a5229d1488d0040ca3dea94318bcb800b00a6b`; F2's documentation head is `95681ce14e54325e54793b625a2381a35c002d04`. G1.5 is not committed or pushed without separate authorization.
