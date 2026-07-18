# ProofLoop Offline Data-Science Evaluation — Final Handoff

**Date:** 2026-07-18
**Track:** Claude — offline data-science evaluation layer
**Branch:** `claude/offline-data-science-evaluation`
**Worktree:** `.worktrees/claude-offlin-science-evaluation`
**Base:** integrated `main` after the Claude documentation checkpoint
**Decision:** **IMPLEMENTED, TESTED, ISOLATED — OFFLINE ANALYTICAL SUPPORT ONLY**
**AWS / Bedrock:** no AWS call, no Bedrock request, no deployment, no
CloudFormation, no schedule change
**Production readiness:** not claimed

---

## Customer outcome

ProofLoop now has an offline evaluation harness that answers the customer's
trust questions about invoice extraction — field trust, failing document
kinds, when to ask a human, financial-harm errors, whether confidence is
meaningful, and latency/token/cost trade-offs — **without ever touching the
deterministic GREEN/AMBER/RED verdict**. The layer is structurally fenced out
of the runtime in both import directions, so measuring and improving the model
carries zero runtime risk.

## Architecture and isolation evidence

`proofloop.evaluation` imports only the Python standard library and Pydantic
(an existing project dependency). It imports no other ProofLoop package and no
cloud SDK. The isolation is enforced by tests, not convention:

- **Forward AST scan** — no evaluation source imports any runtime package
  (`domain`, `agents`, `application`, `infrastructure`, `api`), banned SDK
  (`boto3`, `botocore`, `requests`, `httpx`, `socket`, `urllib`, `pandas`,
  `numpy`, `sklearn`), or runtime verdict type (`EvidenceEnvelope`,
  `AssuranceEvaluation`, `ComplianceReadModel`, `ControlObservation`).
- **Reverse AST scan** — no runtime source imports `proofloop.evaluation`.
- **Clean-subprocess probe** — importing the whole evaluation package pulls
  zero runtime modules and zero banned dependencies into `sys.modules`.
- **Vocabulary guard** — `report.py` is checked to never emit runtime verdict
  fields (`"GREEN"/"AMBER"/"RED"/overall_compliance_status`), so its output
  cannot be mistaken for or spliced into a compliance record.

## Exact files changed

Created (Claude-owned scope only):

- `src/proofloop/evaluation/__init__.py`
- `src/proofloop/evaluation/records.py`
- `src/proofloop/evaluation/normalization.py`
- `src/proofloop/evaluation/metrics.py`
- `src/proofloop/evaluation/calibration.py`
- `src/proofloop/evaluation/report.py`
- `scripts/evaluate_extraction.py`
- `tests/evaluation/__init__.py`
- `tests/evaluation/eval_fixtures.py`
- `tests/evaluation/test_evaluation_records.py`
- `tests/evaluation/test_evaluation_normalization.py`
- `tests/evaluation/test_evaluation_metrics.py`
- `tests/evaluation/test_evaluation_calibration.py`
- `tests/evaluation/test_evaluation_selective.py`
- `tests/evaluation/test_evaluation_report.py`
- `tests/evaluation/test_evaluation_cli.py`
- `tests/evaluation/test_evaluation_isolation.py`
- `docs/submission/DATA_SCIENCE_EVALUATION.md`
- `claude/DATA_SCIENCE_INTERVIEW_GUIDE.md`
- `claude/handovers/FINAL_DATA_SCIENCE_EVALUATION_HANDOFF.md` (this file)
- `docs/superpowers/plans/2026-07-18-proofloop-offline-data-science-evaluation.md`

No runtime source, test, infrastructure, template, workflow, dashboard,
README, deployment/rollback doc, or Codex-owned file was modified. The commit
touched only new evaluation/test/doc files.

## Tests added — exact counts

72 evaluation tests, all passing:

| File | Tests |
|---|---:|
| `test_evaluation_records.py` | 14 |
| `test_evaluation_normalization.py` | 8 |
| `test_evaluation_metrics.py` | 16 |
| `test_evaluation_calibration.py` | 7 |
| `test_evaluation_selective.py` | 5 |
| `test_evaluation_report.py` | 11 |
| `test_evaluation_cli.py` | 6 |
| `test_evaluation_isolation.py` | 5 |
| **Total** | **72** |

Full suite: **349 passed** (was 277 before this track; +72). No existing test
was weakened, skipped, or deleted.

## Metrics implemented

1. Field-level exact match (raw string equality)
2. Field-level normalized match (NFKC → whitespace collapse → casefold)
3. Invoice-level exact match (all expected fields normalized-match)
4. Absolute numeric error (exact Decimal)
5. Relative numeric error (explicit zero-denominator exclusion + count)
6. Schema-valid rate (numeric parseability under the conservative policy)
7. Brier score (binary target = invoice-level normalized match, documented)
8. Calibration bins (10 fixed-width, right-closed last bin)
9. Expected calibration error (count-weighted)
10. Coverage-versus-accuracy / selective-risk table
11. Cost-sensitive confidence-threshold sweep (caller-supplied costs only)
12. Latency summaries (count/min/max/mean/median/nearest-rank p95)
13. Token summaries (present-only totals/means; missing counted, not zeroed)
14. Optional estimated cost summaries (caller-supplied per-1k prices; omitted
    entirely when absent)

Every metric result declares numerator, denominator, value (None on empty),
sample count, missing/zero-denominator exclusion counts, sufficiency status,
kind (`DESCRIPTIVE | CALIBRATION | DECISION_SUPPORT`), and limitations.

## Commands executed — actual results

```text
python -m pytest -q                       -> 349 passed
python -m pytest -q tests/evaluation      -> 72 passed
python -m pytest -q tests/evaluation/test_evaluation_isolation.py \
                    tests/agents/test_agent_isolation.py  -> 7 passed
python -m mypy src/proofloop tests        -> Success: no issues in 105 files
python -m compileall -q src tests scripts infra/scripts   -> exit 0
python scripts/demo_proofloop.py          -> exit 0 (unaffected)
python scripts/demo_agent_to_compliance.py-> exit 0 (unaffected)
PYTHONPATH=src python scripts/evaluate_extraction.py <synthetic dataset> \
  --json-out ... --markdown-out ... --review-cost 1 --error-cost 25 \
  --input-token-price-per-1k 3.00 --output-token-price-per-1k 15.00 \
  --price-currency USD --run-id demo-run
  -> exit 0; status=OK claim_boundary=SYNTHETIC_ONLY; deterministic on rerun
```

Local environment: CPython 3.12.7, Pydantic 2.13.4, pytest 7.4.4 (the base
Anaconda env; the project pins `pytest>=9.0.3,<10` for the declared dev/CI
environment — a version note, not a failure).

## Verification limitations (honest)

- **Ruff, Bandit, and pip-audit are NOT installed in this local environment**
  (`No module named ...`, not on PATH). I did not install software. I make no
  first-hand green claim for them. The new code is written correct-by-
  construction: an over-length-line sweep found and fixed the only two >88-char
  lines; an AST unused-import sweep found none (only `from __future__ import
  annotations`, which is used). Authoritative Ruff/Bandit/pip-audit evidence
  must come from Codex's private CI, exactly as for prior tracks.
- **No real Bedrock call and no customer data** were used. All fixtures are
  synthetic; the report's own `claim_boundary` is `SYNTHETIC_ONLY`.

## Claims permitted

- The evaluation harness exists, is deterministic (byte-identical output on
  identical ordered input + config, excluding `run_metadata`), is fully
  unit-tested (72 tests), and is structurally isolated from the runtime verdict
  path (verified in both import directions).
- All metrics match hand-computed miniature examples (Brier 0.2225, ECE
  0.316666666667, cost sweep 2.75/0.5, etc.).
- Sample sizes are always reported exactly; the report distinguishes computed
  values from conclusions the evidence does or does not support.

## Claims that remain prohibited

- Any production accuracy, calibration, latency, or cost figure — fixtures are
  synthetic; the report says so.
- Any model-superiority conclusion — no real Bedrock request exists.
- Any minimum-sample-size / production-readiness claim.
- Any influence on the runtime compliance verdict, invoice disposition, HITL
  boundary, evidence freshness, payment, or approval — structurally impossible
  and test-enforced.

## Branch and commits

- Documentation checkpoint (canonical `main`): `ad87c31` —
  `docs: reconcile Claude interview documents with G1.6 gate`
- Evaluation implementation (this branch): `0faad45` —
  `feat: add offline data-science evaluation layer`
- Author/committer: `Sri Sruthi Manikka Nagasamy <sruthimanikka@gmail.com>`;
  no AI/bot co-author or attribution trailer.
- Not pushed, not merged.

## Integration risks

- **Low.** The layer adds files under new paths only; it changes no runtime
  behavior, so it cannot regress the deployed slice. The only merge
  consideration is that `main` moved to 277 tests via Codex G1.6 before this
  branch was cut from it, so a merge lands at 349 tests cleanly (this branch
  is already based on the G1.6-integrated `main`).
- **CI note:** Codex's private CI runs Ruff/Bandit/pip-audit; the new files
  should pass, but Codex should confirm since they are the authoritative
  environment for those tools.
- **`AWSCLIV2.pkg`** remains untracked in the canonical worktree; it must
  never be staged (it was not).

## Recommended independent Codex review prompt

> Independently review Claude's `claude/offline-data-science-evaluation`
> branch (commit `0faad45`) as a READ-ONLY audit. Confirm: (1) `proofloop.
> evaluation` imports only stdlib + Pydantic and no runtime package imports
> it — re-run both AST scans and the clean-subprocess probe; (2) the runtime
> GREEN/AMBER/RED verdict, invoice disposition, HITL boundary, and evidence
> freshness are provably unreachable from the evaluation layer; (3) every
> metric's numerator/denominator/zero-denominator/missing-value behavior
> matches the documentation and the hand-computed examples; (4) the
> normalization policy never merges genuinely different invoice values; (5)
> the report's sufficiency and claim-boundary logic blocks production/accuracy
> claims on synthetic data and flags tuning/reporting split misuse. Then run
> Ruff, Bandit, and pip-audit (unavailable in Claude's local env) and the full
> suite in the private CI environment and report exact results. Do not deploy,
> call AWS/Bedrock, change infrastructure, or merge without product-owner
> authorization.

## Five files the human should inspect

1. `tests/evaluation/test_evaluation_isolation.py` — the isolation proof
2. `src/proofloop/evaluation/metrics.py` — sufficiency + numeric error rules
3. `src/proofloop/evaluation/calibration.py` — Brier/ECE/selective/sweep
4. `docs/submission/DATA_SCIENCE_EVALUATION.md` — customer-facing explanation
5. `scripts/evaluate_extraction.py` — validate-before-compute, safe-fail CLI

## Concepts the human must understand

Calibration versus confidence; why the runtime verdict stays deterministic;
threshold selection as a caller-owned business-cost decision; data vs. quality
vs. model-contract drift; split leakage and the tuning/reporting rule; and why
synthetic fixtures verify the harness but support no production claim.
