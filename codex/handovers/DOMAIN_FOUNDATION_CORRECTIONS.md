# ProofLoop Domain Foundation Corrections — Codex Handoff

## Task

Correct and freeze ProofLoop's shared domain contracts after Claude Code's independent review, using test-first reproduction and without editing Claude-owned agent files, committing, pushing, deploying, installing software, or creating cloud resources.

## Customer outcome

The corrected foundation prevents one event from proving multiple obligations, prevents staging or another assurance boundary from greening production, detects partial version-vector drift, preserves usable evidence under bounded clock skew, and rejects contradictory assurance/incident/canary truth at construction. Customers continue to receive deterministic GREEN/AMBER/RED states, structured evidence references, readable control names, and safe recovery actions without an AWS or LLM dependency.

## Files read

- `docs/PROJECT_RULES.md`
- `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`
- `claude/reviews/PROOFLOOP_FOUNDATION_INDEPENDENT_REVIEW.md`
- `docs/superpowers/plans/2026-07-17-proofloop-contracts-foundation.md`
- `pyproject.toml`
- `src/proofloop/domain/models.py`
- `src/proofloop/domain/ports.py`
- `src/proofloop/domain/evaluator.py`
- `tests/domain/test_contracts.py`
- `tests/domain/test_ports.py`
- `tests/domain/test_evaluator.py`

## Files changed

- `.gitignore`
- `pyproject.toml`
- `src/proofloop/domain/models.py`
- `src/proofloop/domain/evaluator.py`
- `tests/domain/test_contracts.py`
- `tests/domain/test_ports.py`
- `tests/domain/test_evaluator.py`
- `tests/domain/test_corrections.py`
- `docs/PROJECT_RULES.md`
- `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`
- `codex/handovers/DOMAIN_FOUNDATION_CORRECTIONS.md`

`src/proofloop/agents/`, `tests/agents/`, and `claude/handovers/` were not edited, formatted, staged, removed, or reverted.

## Review findings resolved

| Finding | Resolution |
|---|---|
| B1 | Mandatory evidence `requirement_id`; evaluator matches exact requirement; multi-requirement regression added |
| H1 | Removed `accepted_outcomes`; PASS-only success is explicit |
| H2 | Evaluation/explanation status and GREEN/non-GREEN reason/control invariants validated |
| H3 | RESOLVED incidents require resolution evidence |
| H4 | PASS canaries require confirmed absence of side effects |
| H5 | Mandatory cloud-neutral `Environment` and `assurance_boundary_id` participate in exact correlation |
| H6 | Exact ten-field provenance moved to each requirement; deterministic-component `None` semantics documented/tested |
| H7 | Per-requirement skew tolerance defaults to five seconds; raw timestamps preserved; excess is AMBER |
| H8 | Test claim narrowed; multi-requirement, count, mixed-state, future, boundary-equality and empty-control dimensions added |
| H9 | Supported range changed to `>=3.12,<3.14`; verified runtime remains honestly labeled 3.12.7; 3.13 stays open |
| M1/M2/M3/M4/M5 | Immutable attributes, static Protocol assignments, scoped dedup, strict boundary documentation, ignore/dev metadata |
| L1/L2/L3 | Explicit reason priority, display names in summaries, distinct clock-skew reason |

## Contract changes

1. `WorkflowExecutionReference` now requires `environment: Environment` and `assurance_boundary_id: str`. Legal environments are `LOCAL`, `DEVELOPMENT`, `TEST`, `STAGING`, and `PRODUCTION`.
2. `EvidenceEnvelope` now requires `requirement_id`. Emit one envelope for each requirement actually observed; never copy one event across requirement IDs.
3. `RequiredEvidenceSpecification` now owns mandatory `expected_provenance`. `ControlDefinition.expected_provenance` no longer exists.
4. `Provenance` now contains `component_version`, `prompt_version`, `model_version`, `policy_version`, `schema_version`, `tool_catalog_version`, `mcp_server_version`, `orchestration_version`, `guardrail_version`, and `runtime_config_version`. The component/policy/schema/orchestration/runtime-config fields are mandatory. Genuinely inapplicable fields use `None`.
5. `accepted_outcomes` is removed. PASS supports GREEN, FAIL is RED, and INCOMPLETE/UNAVAILABLE are AMBER.
6. `EvidenceFreshnessPolicy.clock_skew_tolerance` is configurable and defaults to five seconds.
7. Evidence `attributes` changed from a mutable dictionary to `tuple[EvidenceAttribute, ...]`; keys are unique and canonically sorted, and values are scalar.
8. New reasons: `CLOCK_SKEW_EXCEEDED` and `NO_CONTROLS_DECLARED`.
9. Pydantic validators reject contradictory evaluation/explanation states, unsupported GREEN explanations, evidence-free incident resolution, and unsafe passing canaries.

## Migration instructions for Claude

1. Rebase constructors conceptually onto the new required workflow fields. Use a stable customer-owned assurance-boundary identifier; do not derive an AWS ARN/account/region into the domain model.
2. Replace each control-level provenance argument with an `expected_provenance` on every `RequiredEvidenceSpecification`.
3. Build explicit provenance factories:
   - Agent/model evidence populates component, prompt, model, policy, schema, applicable tool/MCP, orchestration, guardrail, and runtime-config versions.
   - Deterministic evidence keeps the five mandatory versions populated and sets genuinely inapplicable prompt/model/tool/MCP/guardrail fields to `None`.
4. When evidence emission is added, stamp the exact `requirement_id` whose observation was made. If two requirements are observed, emit two independently identifiable source events or two distinct source-event IDs; never relabel one event to prove both.
5. Replace attribute dictionaries such as `{"field": "value"}` with `(EvidenceAttribute(key="field", value="value"),)`. Values must be scalar; sensitive customer payloads do not belong in attributes.
6. Preserve source `observed_at` and ingestion `ingested_at` values. Do not normalize timestamps. The evaluator applies the requirement's skew policy.
7. Treat `StateTransitionExplanation` structured fields as authoritative. A future LLM may polish prose only; it must not construct a different status, reasons, affected controls, evidence IDs, or next actions.
8. Update agent tests to use `Environment.TEST` or `Environment.LOCAL` and a test-only assurance boundary. Never reuse STAGING evidence for PRODUCTION tests.

### Minimal migrated construction

```python
workflow = WorkflowExecutionReference(
    tenant_id="customer-a",
    environment=Environment.TEST,
    assurance_boundary_id="customer-a-test-invoices",
    workflow_id="invoice-processing",
    execution_id="execution-001",
    trace_id="trace-001",
)

provenance = Provenance(
    component_version="extraction-agent-v2",
    prompt_version="extraction-prompt-v2",
    model_version="model-v3",
    policy_version="invoice-policy-v4",
    schema_version="1.0",
    tool_catalog_version="invoice-tools-v2",
    mcp_server_version="invoice-mcp-v1",
    orchestration_version="invoice-flow-v2",
    guardrail_version="invoice-guardrail-v3",
    runtime_config_version="invoice-runtime-v5",
)

requirement = RequiredEvidenceSpecification(
    requirement_id="extraction-schema-check",
    evidence_type=EvidenceType.CONTROL_OUTCOME,
    freshness=EvidenceFreshnessPolicy(max_age=timedelta(minutes=15)),
    expected_provenance=provenance,
    required_source="extraction-agent",
)

event = EvidenceEnvelope(
    evidence_id="evidence-001",
    control_id="invoice-extraction",
    requirement_id=requirement.requirement_id,
    evidence_type=requirement.evidence_type,
    source="extraction-agent",
    source_event_id="source-event-001",
    workflow=workflow,
    outcome=EvidenceOutcome.PASS,
    observed_at=observed_at,
    ingested_at=ingested_at,
    provenance=provenance,
    attributes=(EvidenceAttribute(key="schema_valid", value=True),),
)
```

## Tests added

The new correction suite covers requirement A/B isolation, two same-type requirements, `minimum_count=2`, environment/boundary isolation, prompt/model/tool/guardrail drift, deterministic provenance, partial-mismatch recovery, removed accepted outcomes, all requested cross-model invariants, bounded/excessive clock skew (including future ingestion timestamps), scoped/colliding source IDs, deep attribute immutability, simultaneous RED+AMBER, future evidence, strict remediation equality, empty controls, and display-name summaries. Existing 23 tests were migrated without weakening their behavioral assertions.

## Commands executed and actual results at handoff creation

- Baseline `/opt/anaconda3/bin/python3 -m pytest -q`: 23 passed.
- Fresh pre-fix B1 regression: failed because actual status was GREEN instead of expected AMBER.
- Corrected `/opt/anaconda3/bin/python3 -m pytest tests/domain -q`: 54 passed.
- Final full `/opt/anaconda3/bin/python3 -m pytest -q`: 113 passed and 2 failures in protected `tests/agents/test_agent_isolation.py` after Claude's concurrent files arrived.
- `/opt/anaconda3/bin/python3 -m mypy src/proofloop/domain tests/domain`: success, 8 files.
- Exact `/opt/anaconda3/bin/python3 -m mypy src/proofloop tests/domain`: currently reaches Claude's concurrent agent tree and reports one protected prompt-loader typing error; Codex did not edit that file.
- `/opt/anaconda3/bin/python3 --version`: Python 3.12.7.
- `uv --version` and `ruff --version`: unavailable; neither was installed.

## Production risks checked

Unsupported GREEN, multi-tenant/environment/boundary cross-talk, duplicate/collision scope, event-time order, minimum evidence count, exact provenance drift, stale/incomplete/unavailable/failing evidence, post-remediation recovery, future/ingestion clock skew, immutable forensic metadata, contradictory serialized truth, unsafe canaries, premature incident resolution, cloud dependency leakage, customer-readable explanations, and development-runtime honesty.

## Known limitations

- Domain foundation only; no API, persistence, auth, live ingestion, replay, fault injection, AWS, deployment, or real-world accuracy evidence.
- Python 3.13 has not been executed locally.
- Ruff is declared but unavailable, so no Ruff result is claimed.
- `uv` is unavailable, so no lockfile was created; no installation was attempted.
- The repository has no baseline commit and remains untracked. No commit was authorized.
- The exact full-tree mypy result can be affected by Claude's concurrently changing protected files; the Codex-owned domain/test scope is clean.
- The current full pytest result is also affected by two protected Claude agent-isolation failures; Codex did not modify those files to force a green result.

## Human decisions still required

1. Approve stable assurance-boundary naming conventions for each customer/environment.
2. Ratify which optional provenance dimensions apply to each agent and deterministic component.
3. Choose CI/lock tooling and execute the Python 3.12/3.13 matrix.
4. Authorize a first baseline commit when concurrent work is ready.

## Five files the human should inspect

1. `src/proofloop/domain/models.py`
2. `src/proofloop/domain/evaluator.py`
3. `tests/domain/test_corrections.py`
4. `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`
5. `codex/handovers/DOMAIN_FOUNDATION_CORRECTIONS.md`

## Concepts the human must understand

- Evidence-to-requirement binding prevents one proof from satisfying two obligations.
- Environment and assurance boundary are part of truth, not deployment metadata.
- Provenance is an exact per-requirement version vector.
- Bounded clock skew preserves forensic timestamps while denying implausible evidence GREEN authority.
- PASS-only deterministic assurance and validated structured explanations fence future LLM prose away from the verdict.
- Tests are bounded local evidence, not proof of deployment or real-world model accuracy.

## Recommended Claude review focus

Verify every future evidence emitter uses the exact requirement ID, complete applicable provenance vector, environment and assurance boundary; verify agent result contracts remain isolated from evidence emission until migrated; and verify any LLM explanation layer consumes immutable structured truth without reconstructing it.

## Documentation updated

`docs/PROJECT_RULES.md` now freezes the corrected semantics and customer trade-offs. `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md` now marks B1/H1–H9 accurately, teaches the binding/boundary/provenance/skew concepts, updates interview/demo narratives, and preserves Implemented/Tested/Reviewed/Planned/Not-deployed honesty.

## Git diff summary

There is no base/head commit because the repository still has no baseline commit. Codex made only the owned changes listed above. No file was staged, committed, pushed, deployed, deleted, or provisioned.
