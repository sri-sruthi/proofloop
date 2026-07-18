# ProofLoop Offline Data-Science Evaluation — Repaired Final Handoff

**Date:** 2026-07-19  
**Original Claude head:** `967e05c055c732789720fd5b79042123c10b23b0`  
**Repair branch:** `codex/review-claude-offline-data-science`  
**Decision:** **LOCAL PASS — PRIVATE CI AND INTEGRATION STILL REQUIRED**  
**AWS / Bedrock:** no AWS call, model request, deployment, change set, or
schedule change  
**Production readiness:** not claimed

## Customer outcome

The offline extraction-evaluation layer now fails safely at every confirmed
customer-trust boundary. Records cannot be mutated after validation; raw or
arbitrary payload fields are not representable; incomplete evidence cannot
become a free auto-accept; costs cannot be negative or non-finite; paired CLI
reports cannot be partially published; and the offline evaluation package is
absent from both Lambda artifacts.

The layer remains analytical support only. It cannot reach or change runtime
GREEN/AMBER/RED, invoice disposition, HITL, payment, evidence freshness, AWS,
or Bedrock.

## Repairs completed

1. `EvaluationRecord` defensively copies and freezes expected/predicted field
   mappings while preserving their JSON-object representation.
2. Schema `1.0.0` exposes a bounded invoice-scalar allow-list and conservative
   PII/credential/prompt/control-content guards. These are a structural
   backstop, not enterprise DLP; upstream de-identification remains required.
3. `schema_valid_rate` was removed. The replacement,
   `numeric_prediction_parse_availability_rate`, measures whether expected
   numeric predictions are present and conservatively parseable. It does not
   claim extraction-schema validity.
4. Unjudgeable or incomplete records always route to review. A wholly
   unjudgeable dataset reports `INSUFFICIENT_EVIDENCE` with no supported claim.
5. Review costs, error costs, and token prices must be finite and non-negative
   at direct, configuration, and CLI boundaries.
6. CLI JSON/Markdown publication uses sibling temporary files, atomic replace,
   backup/rollback, safe one-line errors, and cleanup.
7. The Lambda copy helper excludes `proofloop.evaluation`, `__pycache__`,
   `.pyc`, and `.pyo`. Built-handler verification enforces the same boundary
   before and after import.

## Exact repair files

- `src/proofloop/evaluation/records.py`
- `src/proofloop/evaluation/metrics.py`
- `src/proofloop/evaluation/calibration.py`
- `src/proofloop/evaluation/report.py`
- `scripts/evaluate_extraction.py`
- `tests/evaluation/test_evaluation_records.py`
- `tests/evaluation/test_evaluation_metrics.py`
- `tests/evaluation/test_evaluation_selective.py`
- `tests/evaluation/test_evaluation_report.py`
- `tests/evaluation/test_evaluation_cli.py`
- `infra/scripts/copy_runtime_package.py`
- `infra/scripts/verify_built_handlers.py`
- `infra/lambda/Makefile`
- `tests/integration/test_lambda_packaging_isolation.py`
- `tests/integration/test_scheduled_hardening.py`
- `docs/submission/DATA_SCIENCE_EVALUATION.md`
- `claude/DATA_SCIENCE_INTERVIEW_GUIDE.md`
- `claude/handovers/FINAL_DATA_SCIENCE_EVALUATION_HANDOFF.md`
- `codex/handovers/FINAL_CLAUDE_DATA_SCIENCE_INDEPENDENT_REVIEW.md`
- `docs/superpowers/plans/2026-07-19-proofloop-ds-package-repair.md`

No agent, privacy, domain-verdict, API, dashboard, SAM-template, or CI-workflow
implementation changed.

## Test-first evidence

Before implementation, focused regressions reproduced:

- mutable nested field dictionaries;
- arbitrary/raw/prompt/model-output/credential field names;
- PII/credential/prompt/unbounded values and a long-ID false positive;
- missing numeric predictions reporting a vacuous value of one;
- high-confidence incomplete evidence being auto-accepted;
- wholly unjudgeable evidence reporting `OK`;
- negative/non-finite costs and CLI tracebacks;
- partial JSON left behind when Markdown publication failed;
- evaluation/cache content present in both Lambda artifacts.

After the narrow repairs:

```text
focused evaluation + packaging tests  124 passed in 2.05s
evaluation tests collected             117
packaging-isolation tests               7 passed in 0.03s
complete project suite                  401 passed in 3.91s
mypy                                    no issues in 106 source files
Ruff                                    all checks passed
Bandit                                  exit 0
pip-audit --strict                      no known vulnerabilities
compileall                              exit 0
both demos                              exit 0
dashboard JavaScript syntax             exit 0
template structural validator           passed
SAM CLI                                 1.163.0
strict SAM lint                         valid
clean SAM build                         succeeded on CPython 3.13.7 arm64
built handlers                          2 verified
artifact evaluation/cache/bytecode      no matches
artifact secret patterns                no matches
```

The first SAM build attempt was blocked by sandbox DNS. The identical local
build succeeded after approved PyPI access. No AWS endpoint was contacted.

## Determinism evidence

Two independent CLI runs over the same ordered synthetic dataset and config
were byte-identical:

- JSON SHA-256:
  `1fa7a08a8bf4466463717993ca006264ed8bac82c3d7d730215d6ae7a5acdc4f`
- Markdown SHA-256:
  `84637feb3baea55f89b8ff4c1e1cf7131bc1958e2c2b518feead9cf4197143e9`

Result: `status=OK`, `claim_boundary=SYNTHETIC_ONLY`. This proves harness
repeatability only, not production accuracy or model quality.

## Claims permitted

- The repaired evaluation harness is deterministic on identical ordered
  inputs/configuration and rejects the confirmed unsafe boundary cases.
- Runtime and evaluation imports remain isolated in both directions.
- The evaluation package is absent from both clean Lambda artifacts.
- Synthetic fixtures exercise the harness but support no production accuracy,
  calibration, latency, cost, or model-superiority claim.

## Required handoff fields

**Task:** Repair the independently confirmed DS and packaging blockers with
TDD, then run the complete local Python 3.13/SAM gate.

**Customer outcome:** Misleading evidence, unsafe record content, partial
reports, and unnecessary deployed attack surface are blocked by executable
contracts.

**Files read:** Original DS handoff/plan, every evaluation source/test, CLI,
runtime isolation boundaries, packaging Makefile/scripts, CI, SAM template,
DS docs, and project rules.

**Files changed:** Exact list above.

**Review findings resolved:** DS-RECORD-01, DS-METRIC-02, DS-DECISION-03,
DS-EVIDENCE-04, DS-COST-05, DS-CLI-06, and PKG-BOUNDARY-01.

**Contract changes:** Exact seven-item repair list above.

**Migration instructions for Claude:** Use only `INVOICE_SCALAR_FIELDS_V1`
keys; use the new metric name; keep records deeply immutable; route incomplete
evidence to review; preserve transactional publication and runtime isolation.

**Tests added:** 52 beyond the original 349-test branch result; final local
suite count 401.

**Commands executed / actual results:** Recorded above and in the independent
Codex review.

**Production risks checked:** Privacy/content entry, mutability, metric truth,
evidence sufficiency, cost safety, failure atomicity, import isolation,
dependency vulnerabilities, secret patterns, SAM validity, handler imports,
and artifact contents.

**Known limitations:** No customer data, real model call, AWS resource,
deployment, CloudFormation preview, or production performance evidence exists.

**Human decisions still required:** Phase 3 private CI/integration must pass.
AWS work later requires the confirmed non-root profile and explicit deployment
approval gates from the master track.

**Five files the human should inspect:**

1. `src/proofloop/evaluation/records.py`
2. `src/proofloop/evaluation/metrics.py`
3. `scripts/evaluate_extraction.py`
4. `infra/scripts/copy_runtime_package.py`
5. `codex/handovers/FINAL_CLAUDE_DATA_SCIENCE_INDEPENDENT_REVIEW.md`

**Concepts the human must understand:** Deep versus shallow immutability;
parseability versus schema validity; unjudgeable evidence; transactional
multi-file publication; import isolation versus deployment-package isolation.

**Recommended Claude review focus:** Guard false-positive/negative trade-offs,
metric naming, review routing, rollback behavior, and preservation of runtime
verdict isolation.

**Documentation updated:** DS evaluation guide, interview guide, this handoff,
independent review, and repair plan.

**Git diff summary:** Approved DS/test/package/documentation repair only. At
this checkpoint, Phase 3 commit/push/private CI/integration is still pending.
