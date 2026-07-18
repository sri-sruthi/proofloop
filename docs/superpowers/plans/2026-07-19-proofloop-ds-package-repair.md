# ProofLoop DS and Lambda Package Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the six confirmed offline-evaluation contract defects and remove the evaluation package from both Lambda artifacts without changing runtime verdict behavior.

**Architecture:** Keep the evaluation layer self-contained and preserve its versioned JSON record shape. Strengthen its input contracts, make metric and evidence semantics explicit, publish CLI output transactionally, and move Lambda source copying behind a small deterministic packaging helper that excludes offline-only and cache content.

**Tech Stack:** CPython 3.13, Pydantic 2, pytest 9, `Decimal`, AWS SAM custom Make builder, mypy, Ruff, Bandit, pip-audit.

## Global Constraints

- Work only in `.worktrees/review-claude-offline-data-science` until the master track's green-gate integration step.
- Use test-first RED/GREEN cycles for every behavioral repair.
- Preserve runtime compliance verdict, evidence, HITL, payment, agent, privacy, and AWS behavior.
- Do not call AWS, invoke Bedrock, deploy, create a change set, enable the schedule, or expose a secret.
- Do not commit or push until every Phase 2 local gate is green.
- Preserve canonical-main user work and never stage `AWSCLIV2.pkg`.

---

### Task 1: Deeply immutable, bounded evaluation records

**Files:**
- Modify: `tests/evaluation/test_evaluation_records.py`
- Modify: `src/proofloop/evaluation/records.py`

**Interfaces:**
- Consumes: version `1.0.0` record JSON with `expected_fields` and `predicted_fields` objects.
- Produces: immutable `Mapping[str, str | None]` values that still serialize as JSON objects.
- Produces: `INVOICE_SCALAR_FIELDS_V1`, the explicit scalar allow-list for record schema `1.0.0`.

- [x] Add tests proving caller-owned dictionaries are defensively copied and `record.expected_fields["total"] = ...` raises `TypeError`.
- [x] Add parameterized tests rejecting field names `raw_invoice`, `prompt`, `model_output`, `credential`, `secret`, and an arbitrary payload key while accepting the canonical invoice scalar fields used by existing fixtures.
- [x] Add tests rejecting email, phone-shaped, AWS-access-key, bearer-token, private-key-header, prompt-role-marker, multiline, control-character, and overlength values across mappings and metadata; retain tests for ordinary vendor names and invoice/PO identifiers.
- [x] Run the focused record tests and verify each new assertion fails for the intended missing guard or shallow mutation.
- [x] Change field annotations to `Mapping[str, str | None]`; validate keys/values; return `MappingProxyType(dict(value))`; serialize mappings with Pydantic `field_serializer` so the external JSON object shape stays stable.
- [x] Apply the conservative sensitive-text validator to identifiers, tags, configuration IDs, and run ID without importing runtime privacy code.
- [x] Run record, serialization, metric, and report tests and verify green.

### Task 2: Honest numeric prediction metric

**Files:**
- Modify: `tests/evaluation/test_evaluation_metrics.py`
- Modify: `tests/evaluation/test_evaluation_report.py`
- Modify: `src/proofloop/evaluation/metrics.py`
- Modify: `src/proofloop/evaluation/report.py`
- Modify: `src/proofloop/evaluation/__init__.py`

**Interfaces:**
- Removes: `schema_valid_rate` and metric ID `schema_valid_rate`.
- Produces: `numeric_prediction_parse_availability_rate(records) -> MetricResult` and metric ID `numeric_prediction_parse_availability_rate`.
- Definition: among records with at least one expected numeric field, the numerator counts records where every expected numeric field is present and parseable in predictions; records with no expected numeric field are excluded and counted.

- [x] Add tests proving a missing expected numeric prediction fails the metric, an unparseable prediction fails it, and a record with no expected numeric field is excluded rather than vacuously valid.
- [x] Update existing imports/assertions to the honest name, then run the focused metric tests and verify RED because the new function is absent.
- [x] Implement the exact denominator, numerator, exclusion, sufficiency, and limitation text above.
- [x] Replace report/export references and scan source/tests/reviewer docs to ensure no current claim calls parseability schema validity.
- [x] Run focused metric/report tests and verify green.

### Task 3: Unjudgeable evidence and safe threshold decisions

**Files:**
- Modify: `tests/evaluation/test_evaluation_calibration.py`
- Modify: `tests/evaluation/test_evaluation_report.py`
- Modify: `src/proofloop/evaluation/calibration.py`
- Modify: `src/proofloop/evaluation/report.py`

**Interfaces:**
- A record is decision-eligible only when expected fields are nonempty and every expected field is present in predictions.
- Ineligible records route to review regardless of confidence.
- A report is `OK` only when at least one record has nonempty expected evidence; otherwise it is `INSUFFICIENT_EVIDENCE` with no supported claim.

- [x] Add tests for high-confidence empty expected/predicted fields and high-confidence missing predicted fields; require review routing, zero auto-accept, and zero wrong-auto-accept.
- [x] Add a report test requiring a wholly unjudgeable dataset to return `INSUFFICIENT_EVIDENCE` and no supported claims.
- [x] Run these tests and verify the current zero-cost auto-accept and `OK` results fail them.
- [x] Add a small decision-eligibility helper and make `threshold_cost_sweep` route ineligible records to review before threshold comparison.
- [x] Derive report sufficiency from usable expected evidence rather than tuple length; only attach supported computation claims when sufficient.
- [x] Run calibration/report/evaluation tests and verify green.

### Task 4: Finite non-negative costs and prices

**Files:**
- Modify: `tests/evaluation/test_evaluation_calibration.py`
- Modify: `tests/evaluation/test_evaluation_report.py`
- Modify: `tests/evaluation/test_evaluation_cli.py`
- Modify: `src/proofloop/evaluation/calibration.py`
- Modify: `src/proofloop/evaluation/report.py`
- Modify: `scripts/evaluate_extraction.py`

**Interfaces:**
- `review_cost`, `error_cost`, and both token prices accept finite Decimal-compatible values greater than or equal to zero.
- Negative, `NaN`, `Infinity`, and `-Infinity` values fail validation and the CLI returns code 2 without traceback or output.

- [x] Add direct configuration and sweep tests for the invalid values and valid zero values.
- [x] Add CLI tests for invalid cost/price inputs that assert return code 2, no traceback, and no output file.
- [x] Run the focused tests and verify RED.
- [x] Validate Decimal finiteness/non-negativity at both the Pydantic configuration boundary and the directly callable sweep boundary; convert validation failures to `SafeCliError`.
- [x] Run calibration/report/CLI tests and verify green.

### Task 5: Transactional CLI output publication

**Files:**
- Modify: `tests/evaluation/test_evaluation_cli.py`
- Modify: `scripts/evaluate_extraction.py`

**Interfaces:**
- `_publish_outputs(outputs: Mapping[Path, str]) -> None` preflights targets, writes sibling temporary files, and publishes only after all temporary writes succeed.
- Any failure removes temporary/new partial outputs, restores pre-existing targets when replacement began, raises `SafeCliError`, and prints no traceback or sensitive content.

- [x] Add a subprocess test using a valid JSON target and an existing directory as the Markdown target; assert return code 2, no traceback, and no new JSON file.
- [x] Add a test proving pre-existing output files remain unchanged when the paired publication fails.
- [x] Run the two tests and verify the current sequential writer fails them.
- [x] Implement output-target preflight, sibling temp files with restrictive defaults, backup/rollback for existing targets, `os.replace` publication, and unconditional temporary cleanup.
- [x] Route publication errors through the existing safe CLI error path.
- [x] Run all CLI tests plus two-run byte-repeatability checks and verify green.

### Task 6: Lambda artifact isolation

**Files:**
- Create: `infra/scripts/copy_runtime_package.py`
- Create: `tests/integration/test_lambda_packaging_isolation.py`
- Modify: `infra/lambda/Makefile`
- Modify: `infra/scripts/verify_built_handlers.py`

**Interfaces:**
- `copy_runtime_package(source: Path, destination: Path) -> None` copies the runtime package while excluding only root `proofloop/evaluation`, every `__pycache__` directory, and every `*.pyc` file.
- `verify_artifact_isolation(artifact: Path) -> None` rejects evaluation, cache, and bytecode paths in a built artifact.

- [x] Add unit tests that copy a synthetic package tree and assert runtime modules remain while evaluation/cache/bytecode files do not.
- [x] Add verifier tests that reject each prohibited artifact path and accept a clean artifact.
- [x] Run the new tests and verify RED because the helper/verifier do not exist.
- [x] Implement the deterministic copy helper without project/runtime imports and invoke it from both Make targets instead of `cp -R`.
- [x] Extend built-handler verification to call the isolation check before imports.
- [x] Run integration tests, template structural validation, clean SAM build, both handler imports, and artifact scans; require evaluation/cache/bytecode absence.

### Task 7: Reconcile documentation and independent verdict

**Files:**
- Modify: `docs/submission/DATA_SCIENCE_EVALUATION.md`
- Modify: `claude/DATA_SCIENCE_INTERVIEW_GUIDE.md`
- Modify: `claude/handovers/FINAL_DATA_SCIENCE_EVALUATION_HANDOFF.md`
- Modify: `codex/handovers/FINAL_CLAUDE_DATA_SCIENCE_INDEPENDENT_REVIEW.md`

**Interfaces:**
- Documentation uses the honest metric name/definition, states the bounded structural guard is not enterprise DLP, and states evaluation is absent from Lambda artifacts only after artifact verification passes.
- The independent review retains original failure evidence and records each repair/test before changing its verdict.

- [x] Update metric tables and narrative; remove current “schema validity” terminology for numeric parseability.
- [x] Document deep immutability, bounded scalar allow-list, unjudgeable review routing, finite-cost validation, transactional publication, and package exclusion.
- [x] Preserve the original FAIL findings in the independent review and append repair evidence; change the final verdict only after Task 8 passes.
- [x] Scan documentation for stale or contradictory claims.

### Task 8: Complete authoritative Phase 2 gate

**Files:**
- Modify only the review document if exact command evidence needs reconciliation.

**Interfaces:**
- Produces the binary local PASS/FAIL decision controlling Phase 3.

- [x] Run all evaluation and adversarial tests in disposable CPython 3.13.
- [x] Run the complete pytest suite, mypy, Ruff, Bandit, strict pip-audit, and compileall.
- [x] Run both demos, CLI deterministic repeatability, import-isolation scans, and secret/PII/credential scans.
- [x] Run the template validator, strict SAM lint, a clean SAM build, both built-handler imports, evaluation/cache/bytecode artifact scans, and dashboard JavaScript syntax.
- [x] Record exact versions, commands, counts, exit codes, hashes, and any accepted tooling advisory in the independent review.
- [x] Inspect `git status`, `git diff --check`, the complete diff, canonical-main status, and `AWSCLIV2.pkg` preservation.
- [x] If every result is green, set the independent review verdict to PASS and proceed to the separately gated Phase 3 commit/private-CI/integration workflow; otherwise stop with exact red evidence.
