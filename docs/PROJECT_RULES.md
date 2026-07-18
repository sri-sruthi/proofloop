# ProofLoop Project Rules

## Canonical product definition

ProofLoop implements **PS-6.2: Runtime-to-Compliance Evidence Assurance Platform** for production AI agents. It determines whether declared controls are actually executing, producing the intended outcome, and supported by fresh runtime evidence. The reference workload is a two-agent invoice workflow—extraction followed by reconciliation—with deterministic simulated execution behind a human-approval boundary.

This document and the product owner's current task instructions are authoritative. Older Agent WAF, Sentinel, Vigil, AegisFlow, or maximal AgentCore proposals are historical research, not implementation requirements.

## Customer as the fifth element

Every material decision must identify the affected persona, the uncertainty resolved, possible customer harm, the evidence or recovery mechanism provided, and how value is measured without unacceptable privacy, latency, or cost.

Permanent promises:

1. **No unsupported green:** GREEN always has sufficient, consistent, fresh runtime evidence.
2. **No surprise shutdown:** uncertain evidence produces an explainable AMBER response and a proportionate next action.
3. **No black-box score:** every state has reason codes, affected controls, supporting evidence, and a readable explanation.
4. **No vendor lock-in:** domain contracts and evaluation remain cloud-neutral.
5. **No hidden cost:** infrastructure and model consumption must be attributable and bounded.
6. **No unsafe canary:** canaries use reserved synthetic data and only no-op or sandbox side effects.
7. **No premature recovery:** remediation or configuration changes require new positive evidence before GREEN.

## Architectural invariants

- The domain core imports no AWS SDK, agent framework, MCP runtime, or LLM client.
- Infrastructure implements ports; infrastructure types never leak into domain models.
- Final assurance state is deterministic. Probabilistic signals can support but never independently declare GREEN.
- Every evidence event names exactly one `requirement_id`; it can satisfy only that requirement.
- Exact correlation includes assurance boundary, environment, tenant, workflow, execution, trace, control, requirement, evidence type, required source, and current provenance.
- Deployment environments are cloud-neutral: LOCAL, DEVELOPMENT, TEST, STAGING, and PRODUCTION. A canary is an evidence behavior, not an environment.
- Expected provenance belongs to each evidence requirement and is matched by exact version-vector equality.
- Deterministic components set genuinely inapplicable prompt, model, tool, MCP, and guardrail versions to `None`; all mandatory component, policy, schema, orchestration, and runtime-config versions remain populated.
- PASS is the only outcome that supports GREEN. FAIL is RED; INCOMPLETE and UNAVAILABLE are AMBER. This behavior is not configurable.
- Missing, incomplete, inconsistent, unavailable, uncorrelated, or stale evidence maps to AMBER/UNKNOWN.
- Current, unambiguous evidence of a required-control failure maps to RED.
- GREEN requires every required evidence specification to pass freshness, correlation, provenance, and outcome checks.
- Evidence is evaluated by event time, not input or ingestion order.
- Duplicate identity is scoped by tenant, environment, assurance boundary, workflow, source, and source-event ID. Legitimate reuse outside that scope cannot collide; conflicting reuse inside it is AMBER.
- Evidence attributes are a canonical tuple of unique, immutable scalar attributes; accepted evidence cannot be mutated after validation.
- The default distributed-clock-skew tolerance is five seconds per evidence freshness policy. Raw UTC timestamps are preserved; excessive ingestion/future skew is explainable AMBER and never GREEN.
- Recovery evidence must be observed strictly after the remediation or version-change time and match current per-requirement provenance. Equality with the boundary is insufficient.
- Serialized truth must be internally consistent: evaluation and explanation status agree, GREEN has only the success reason and no affected controls, resolved incidents carry resolution evidence, and PASS canaries confirm absence of side effects.
- Every state transition is explainable to both machines and customers.
- Canary definitions must preclude real customer-side effects.
- UTC-aware timestamps, typed validation, idempotency, privacy, bounded retries, backpressure, observability, and customer-visible failure behavior are production requirements.

## Production-readiness definition

Code existence is not production readiness. A feature may be called production-ready only after its applicable contracts, authentication/authorization, concurrency, failure behavior, privacy/retention, observability, cost limits, rollback/recovery, and unit/property/contract/integration/failure-injection tests have been implemented and verified in the target environment. This foundation is a verified domain slice, not a claim that the complete platform is production-ready.

The supported local package range is Python `>=3.12,<3.14`. The foundation is locally verified on Python 3.12.7. Python 3.13 is the intended later AWS Lambda runtime but remains unverified until CI or a local 3.13 environment executes the complete checks.

## Customer decision record for the frozen corrections

| Decision | Persona and failure prevented | Evidence/explanation and safe recovery | Privacy, latency and cost |
|---|---|---|---|
| Requirement-bound evidence | Operator relying on a release/payment green; prevents one event proving two obligations | Missing bound evidence is AMBER with the affected control and its next safe action; emit one event per requirement | One small identifier per event; no new sensitive data, network call, or model cost |
| Environment and assurance-boundary isolation | Production owner; prevents staging or another customer boundary greening production | Mismatches are `EVIDENCE_UNCORRELATED`; inspect routing and re-emit evidence from the correct boundary | Local enum/identifier comparison only; negligible latency and cost |
| Per-requirement provenance vector | Control owner; prevents recovery after a prompt/model/tool/guardrail/runtime downgrade | Exact mismatch is `OBSOLETE_PROVENANCE`; deploy current versions and produce new evidence | Version identifiers only; no prompt content or customer payload is stored |
| Fixed PASS-only truth and cross-model validation | Customer/API consumer; prevents contradictory or silently ignored configuration | Invalid objects fail at validation; uncertainty remains AMBER and explicit failure remains RED | Local validation only; avoids LLM calls and hidden operational cost |
| Bounded clock skew | Distributed-system operator; prevents legitimate evidence being dropped while blocking implausible future proof | Up to policy tolerance is accepted unchanged; excess is `CLOCK_SKEW_EXCEEDED` with investigation guidance | Raw forensic timestamps retained; constant-time arithmetic, no extra storage beyond existing fields |
| Scoped deduplication | Multi-tenant operator; prevents cross-tenant false collisions and same-boundary ambiguous reuse | Cross-scope reuse is independent; conflicting reuse inside the scope is `EVIDENCE_CONFLICT` | Uses existing identifiers; deterministic in-memory grouping with no external service cost |
| Immutable scalar attributes | Auditor and incident responder; prevents post-validation evidence mutation | Canonically sorted typed attributes remain stable for replay and duplicate comparison | Scalar-only metadata limits privacy exposure and avoids a new immutability dependency |
| Reproducible local tooling | Developer/reviewer; prevents unsupported runtime and lint claims | Supported range, actual runtime, declared pytest/mypy/Ruff dependencies, ignore rules, and honest lockfile limitation are documented | No system install, cloud resource, or paid service was introduced |

## Ownership boundaries

Codex owns canonical domain contracts, evidence schemas and correlation, deterministic assurance state, canaries, replay/fault injection, evaluation, API/persistence/AWS adapters, IaC, CI/CD, observability, and deployment verification.

Claude Code owns invoice agents, prompts, MCP tools, the model-provider abstraction, agent memory/handoffs, agent guardrail middleware, and customer-facing AI-generated explanations.

Shared contracts require review before broad implementation. One owner edits a file at a time. Neither assistant changes the other's files without an explicit handoff from the product owner.

## Verification before completion

No completion claim is allowed without fresh evidence. Before handoff:

1. Run every configured formatter, linter, type checker, and relevant test suite.
2. Run the full bounded test suite and inspect actual failures/warnings.
3. Review the Git diff and run whitespace/patch checks.
4. Confirm no cloud or agent dependency leaked into the domain core.
5. Map each acceptance criterion to a named test or inspected artifact.
6. Report actual commands/results, limitations, and unresolved decisions.
7. Do not weaken or delete a test to obtain a passing result.

## Handoff format

Every handoff must include:

```text
Task:
Customer outcome:
Files read:
Files changed:
Review findings resolved:
Contract changes:
Migration instructions for Claude:
Tests added:
Commands executed:
Actual results:
Production risks checked:
Known limitations:
Human decisions still required:
Five files the human should inspect:
Concepts the human must understand:
Recommended Claude review focus:
Documentation updated:
Git diff summary:
```

Include the base/head commit when commits exist. Until the product owner authorizes Git mutations, report that the repository has no baseline commit and do not commit, push, deploy, or create billable resources.
