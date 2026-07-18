# ProofLoop Track D2 Release-Candidate Design

**Date:** 2026-07-18  
**Owner:** Codex release-candidate QA and submission packaging  
**Authority:** Product-owner Track D2 brief  
**Status:** Approved by the explicit instruction to proceed; documentation-only execution

## Goal

Produce a locally verified PS-6.2 release-candidate evidence package without
changing the implementation, invoking AWS or a real model, mutating Git, or
claiming production readiness.

## Constraints

- Writable ownership is limited to `docs/**` and `codex/**`.
- `src/**`, `tests/**`, `infra/**`, `dashboard/**`, `claude/**`, and `README.md`
  are read-only.
- No AWS, Bedrock, cloud-resource, GitHub, commit, push, or deployment action.
- Manual scenarios use reserved synthetic data only and never expose the local
  API key, raw PII, prompts, model output, or hidden reasoning.
- A discovered implementation defect is recorded as a release blocker and is
  not silently repaired during Claude's independent audit.

## Considered approaches

1. **One monolithic final report.** Simple delivery, but weak traceability and a
   poor operator experience because test evidence, demo steps, and deployment
   decisions become difficult to find.
2. **Screenshot-first submission.** Visually persuasive, but brittle, hard to
   reproduce, and likely to over-emphasize UI polish over exact assurance
   semantics.
3. **Evidence matrix plus purpose-built artifacts (selected).** One canonical
   write-up is supported by a QA ledger, demo runbook, deployment/rollback
   checklist, and release handoff. Screenshots are used only where visual state
   materially helps and are cross-referenced to text evidence.

## Evidence architecture

```text
Assignment + project rules + current handoffs
  -> clean local command gate
  -> synthetic manual API/dashboard scenarios
  -> normalized evidence ledger (command, expected, actual, verdict)
  -> final Markdown write-up
  -> professionally rendered and page-inspected PDF
  -> predeployment release-gate handoff
```

Command evidence records the exact executable, runtime, exit code, and concise
result. Manual evidence records synthetic input class, observable response/state,
privacy inspection, and PASS/FAIL/BLOCKED. No evidence file stores request
secrets or raw synthetic PII values.

## Submission structure

- `docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.md`: canonical assessment
  narrative, architecture, differentiation, evidence, limitations, and local
  run instructions.
- `docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.pdf`: styled, paginated review
  artifact generated from the same verified facts and inspected visually.
- `docs/submission/DEMO_RUNBOOK.md`: five-to-eight-minute local narration with
  preflight, commands, expected states, recovery, and privacy cautions.
- `docs/submission/MANUAL_QA_EVIDENCE.md`: fourteen-scenario ledger plus release
  commands, environment, screenshots, and unavailable checks.
- `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`: post-activation choices,
  guarded build/deploy/smoke/rollback steps, evidence capture, and owners.
- `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`: exact verdict, blockers,
  Claude findings ownership, Git hygiene, next prompt, and five inspection files.
- `docs/submission/evidence/`: customer-safe screenshots only when useful.

## Manual QA design

The API is composed with the fake model provider and an ephemeral local API key.
HTTP boundary checks use the local WSGI path. State-machine and injected failure
scenarios use the same production composition contracts through deterministic
in-process fixtures where the public local server cannot configure a malformed
provider or tool timeout. Dashboard QA loads its real static files against the
local API and checks visible compliance, timeline, incident, reason, and safe
action rendering.

Each of the fourteen required scenarios receives one of:

- `PASS`: observed behavior matches the approved contract;
- `FAIL`: a release-candidate defect was reproduced;
- `BLOCKED`: a required tool/runtime is unavailable and no honest equivalent
  exists.

## PDF design

The PDF uses a restrained navy/teal/red status palette, one sans-serif body
family, consistent headers/footers, numbered sections, compact evidence tables,
and vector architecture/data-flow diagrams. Status labels always distinguish
Implemented, Tested, Reviewed, Planned, and Not Deployed. The renderer uses only
repository facts and local evidence. Every page is rendered to PNG and inspected
for clipping, overlap, broken glyphs, table overflow, hierarchy, and legibility.

## Failure handling

- A failed release command is captured verbatim enough to reproduce, without
  leaking environment secrets.
- A manual scenario failure stops only that scenario and becomes a blocker.
- Unavailable SAM/Python 3.13/security tools remain explicit gaps; workflow-file
  presence is never reported as executed CI.
- Claude review findings are referenced with Claude as next code owner unless the
  product owner separately authorizes implementation.

## Acceptance mapping

The final handoff must identify the local verdict, all fourteen manual outcomes,
all six required artifacts, blocked/unavailable checks, the exact post-AWS
activation prompt, and five files for the human demo review. No status may be
upgraded beyond the evidence produced during this Track D2 run.
