# ProofLoop Offline Data-Science Evaluation Layer — Design and Implementation Plan

**Date:** 2026-07-18
**Track:** Claude — offline data-science evaluation layer
**Branch:** `claude/offline-data-science-evaluation`
**Base:** integrated main after the Claude documentation checkpoint (`ad87c31`)
**Verdict sought:** offline analytical support only — never a runtime authority

## Customer as the fifth element

Each deliverable answers a named customer question:

| Customer question | Deliverable |
|---|---|
| Can I trust the extracted invoice fields? | field-level exact/normalized match, invoice-level exact match |
| Which kinds of documents are failing? | per-category/difficulty/source breakdowns from record tags |
| When should the workflow ask a human for help? | coverage-versus-accuracy (selective risk) table, cost-sensitive threshold sweep |
| Which errors could cause financial harm? | absolute/relative numeric error on money fields, cost-weighted sweep |
| Is model-reported confidence meaningful? | Brier score, calibration bins, expected calibration error |
| Latency/token/cost trade-offs? | latency summaries, token summaries, optional caller-priced cost estimate |
| Is quality degrading for a category/source? | split- and tag-scoped metric tables comparable across runs |

## Non-negotiable boundary

The GREEN/AMBER/RED verdict stays deterministic. Nothing in
`proofloop.evaluation` may create, modify, override, or suppress a runtime
compliance verdict, approve an invoice, release a payment, bypass HITL, or
alter evidence freshness. Enforced structurally, not by convention:

1. `proofloop.evaluation` imports only the Python standard library and
   Pydantic (an existing project dependency). It imports **no** other
   `proofloop` package — not `domain`, not `agents`, not `application`,
   not `infrastructure`, not `api`.
2. No runtime package imports `proofloop.evaluation`. Both directions are
   locked by AST + clean-interpreter isolation tests, mirroring
   `tests/agents/test_agent_isolation.py`.
3. The CLI reads a record file and writes JSON/Markdown. It has no AWS
   client, no network access, and no handle to evidence or assurance state.

## Scope (only these paths)

- `src/proofloop/evaluation/` — new package
- `tests/evaluation/` — new tests
- `scripts/evaluate_extraction.py` — CLI
- `docs/submission/DATA_SCIENCE_EVALUATION.md`
- `claude/DATA_SCIENCE_INTERVIEW_GUIDE.md`
- `claude/handovers/FINAL_DATA_SCIENCE_EVALUATION_HANDOFF.md`
- this plan document

## Data contract — `EvaluationRecord` schema 1.0.0

Versioned, PII-free, immutable (Pydantic v2, `extra="forbid"`, `frozen=True`):

- `schema_version` (literal `"1.0.0"`)
- `dataset_record_id`
- `dataset_provenance`: `SYNTHETIC | PUBLIC | DEIDENTIFIED_CUSTOMER`
- `split`: `DEVELOPMENT | VALIDATION | HOLDOUT`
- `expected_fields`, `predicted_fields`: `dict[str, str | None]`
- `model_reported_confidence`: `float | None` in `[0, 1]` — out-of-range
  rejected at validation; missing never becomes zero
- `provider_config_id`, `prompt_config_id`
- `latency_ms` (int ≥ 0), `input_tokens` / `output_tokens` (optional int ≥ 0)
- `tags`: optional `difficulty`, `category`, `source`
- `run_id`: optional run identifier (documented run metadata, excluded from
  determinism comparison)

Prohibited content (best-effort structural guard + documented policy): raw
invoices, prompts, credentials, customer identifiers, unredacted PII, full
model responses, tool payloads, AWS secrets. A conservative validator rejects
e-mail-shaped values and long separator-joined digit runs in field values;
the documentation states this is a guard, not a DLP guarantee.

## Metrics (deterministic, stdlib + Decimal only)

Every metric result carries: metric id, kind
(`DESCRIPTIVE | CALIBRATION | DECISION_SUPPORT`), numerator, denominator,
value (None when the denominator is zero), sample count, missing-value counts,
split, provenance counts, sufficiency status, and limitations.

1. Field-level exact match (raw string equality; None==None counts as match
   only when both sides are None — documented)
2. Field-level normalized match (NFKC → whitespace collapse → casefold)
3. Invoice-level exact match (all compared fields normalized-match)
4. Absolute numeric error on numeric fields (Decimal; unparseable excluded
   and counted)
5. Relative numeric error — zero expected denominator excluded from the mean
   and counted separately (`zero_denominator_count`), never divided
6. Schema-valid rate (records whose predicted fields parse under the numeric
   policy for all numeric fields present)
7. Brier score — binary target is **invoice-level normalized match** (documented);
   only records with a confidence value participate
8. Calibration bins — 10 fixed-width bins, right-closed last bin `[0.9, 1.0]`
9. Expected calibration error (weighted |accuracy − mean confidence|)
10. Coverage-versus-accuracy / selective-risk table over the confidence grid
11. Cost-sensitive confidence-threshold sweep with **caller-supplied** costs
    (`review_cost`, `error_cost`) — no hard-coded pricing or costs
12. Latency summaries (count/min/max/mean/median/p95 nearest-rank)
13. Token summaries (input/output, present-only, missing counted)
14. Optional estimated cost summaries using caller-supplied per-1k token
    prices; absent pricing → section omitted, never guessed

## Evidence-sufficiency rules

- Empty input → report status `INSUFFICIENT_EVIDENCE`; no metric values.
- All-synthetic provenance → `SYNTHETIC_ONLY`: the report states the harness
  is verified but **no production accuracy or calibration claim is supported**.
- No number is called "accuracy" unless labels come from a trusted split;
  synthetic labels are labeled "fixture agreement".
- Missing confidence is excluded and counted, never coerced to 0.
- Probabilities outside [0, 1] are rejected at validation.
- The same `dataset_record_id` in more than one split is a leakage error and
  the report refuses to compute.
- Threshold tuning happens on a tuning split (default DEVELOPMENT); if the
  reporting split equals the tuning split, the sweep is labeled
  `SPLIT_MISUSE` and the "selected threshold performance" claim is withheld.
- Small samples: the exact n is always reported; no invented minimum-n claim.
- The report separates `computed_values` from `supported_claims` and
  `unsupported_claims`.

## Normalization policy (conservative, tested)

- Text: `unicodedata.normalize("NFKC", s)` → collapse whitespace runs to one
  space → strip → `casefold()`.
- Numbers: optional sign, digits, at most one decimal point, surrounding
  whitespace only. **No** currency-symbol or thousands-separator stripping —
  `"1,234"` is not silently equal to `"1234"`. Unparseable values are excluded
  and counted, never guessed.

## Output

- Deterministic JSON (`sort_keys=True`, Decimal serialized as string) and
  Markdown rendered from the same data. Identical ordered records + config →
  byte-identical outputs, excluding only the documented `run_id` metadata.

## CLI — `scripts/evaluate_extraction.py`

- Input: dataset JSON `{"schema_version": "1.0.0", "records": [...]}`.
- Validates fully before computing; exits 2 with a one-line safe error on
  invalid input (no traceback, no partial output).
- Optional `--input-token-price-per-1k`, `--output-token-price-per-1k`,
  `--price-currency`, `--review-cost`, `--error-cost`, `--tuning-split`,
  `--report-split`, `--run-id`.
- Writes `--json-out` and `--markdown-out`. Never calls AWS/Bedrock; never
  touches runtime evidence or compliance state.

## TDD order

1. RED: record schema tests (validity, invalid probability, PII guard,
   leakage detection) → GREEN `records.py`.
2. RED: normalization tests → GREEN `normalization.py`.
3. RED: match/numeric/schema-rate metric tests → GREEN `metrics.py`.
4. RED: Brier/bins/ECE/selective/sweep tests → GREEN `calibration.py`.
5. RED: report+sufficiency+determinism tests → GREEN `report.py`.
6. RED: CLI tests → GREEN `scripts/evaluate_extraction.py`.
7. RED: two-direction isolation tests → GREEN (structural, no code change
   expected).
8. Full gate: pytest, mypy, compileall, demo scripts unaffected; Ruff/Bandit/
   pip-audit honestly reported if unavailable locally.

## Dependencies

Standard library + existing Pydantic only. No pandas/NumPy/scikit-learn/
notebooks/plotting/cloud/tracking. If a need emerges, stop and report first.
