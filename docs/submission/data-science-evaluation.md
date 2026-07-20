# ProofLoop Offline Data-Science Evaluation

**Status:** implemented and tested offline. Runs on local files only — no AWS,
no Bedrock, no runtime state. Every number in this layer is analytical
support; the GREEN/AMBER/RED compliance verdict remains a deterministic pure
function that this layer can neither reach nor change.

---

## 1. What was built

An offline evaluation harness for the invoice-extraction workload:

- **A versioned, bounded data contract** (`EvaluationRecord`, schema 1.0.0)
  describing one labeled extraction outcome: expected fields, predicted
  fields, model-reported confidence, provider/prompt configuration
  identifiers, latency, token counts, provenance, and split. Field mappings
  are defensively copied, deeply immutable, and limited to the declared
  invoice-scalar allow-list. Conservative PII/credential/content refusal
  gates are a backstop, not an enterprise DLP replacement.
- **Deterministic metrics** (`proofloop.evaluation`): match rates, numeric
  errors, numeric-prediction parse/availability rate, Brier score,
  calibration bins, expected
  calibration error, selective risk, a cost-sensitive threshold sweep, and
  latency/token/cost summaries.
- **A CLI** (`scripts/evaluate_extraction.py`) that validates before
  computing and transactionally publishes deterministic JSON (for machines)
  and Markdown (for humans). A paired-output failure restores existing files
  and leaves no new partial report.

The same ordered records and configuration always produce byte-identical
output, excluding only the documented `run_metadata` (run identifier).

## 2. The customer question behind each metric

| Metric | Customer question it answers |
|---|---|
| Field exact / normalized match | Can I trust each extracted invoice field? |
| Invoice-level match | How often is the whole invoice right end to end? |
| Absolute / relative numeric error | Which errors could cause financial harm, and how big are they? |
| Numeric-prediction parse/availability rate | When a numeric field is expected, is its prediction present and conservatively parseable? |
| Brier score, calibration bins, ECE | Is model-reported confidence meaningful? |
| Coverage-versus-accuracy (selective risk) | When should the workflow ask a human for help? |
| Cost-sensitive threshold sweep | Where is *my* cheapest trade-off between review effort and error cost? |
| Latency / token / cost summaries | What are the latency, token, and estimated cost trade-offs? |
| Per-category / difficulty / source tags, per split | Which kinds of documents are failing? Is quality degrading somewhere specific? |

## 3. The formulas, in plain language

**Field match rate.** Numerator: records where the predicted value equals the
expected value. Denominator: records that expect that field at all. Two
flavors: *exact* (character-for-character) and *normalized* (after the
conservative cleanup in §6). Analogy: grading a spelling test strictly versus
accepting different capitalization.

**Invoice-level match.** An invoice counts as right only if *every* expected
field matches (normalized). One wrong field fails the whole invoice — exactly
how an accounts-payable clerk would judge it.

**Absolute numeric error.** For money fields: `|predicted − expected|`,
averaged over parseable pairs. A worked miniature: expected 100.00 and
predicted 90.00 → error 10.00; expected 50 and predicted 50 → error 0; mean
= 5. Money is compared as exact decimals, never binary floats.

**Relative numeric error.** `|predicted − expected| ÷ |expected|`. When the
expected value is 0, division is undefined — those records are **excluded
from the mean and counted separately** (`excluded_zero_denominator`), never
divided or guessed.

**Numeric-prediction parse/availability rate.** Among records with at least
one expected numeric field, the share where every expected numeric prediction
is present and parses as a plain decimal. Records with no expected numeric
field are excluded and counted. This is deliberately **not** called schema
validation: it does not validate the complete extraction schema.

**Brier score.** For every record with a confidence value:
`(confidence − outcome)²`, averaged, where the **binary target is
invoice-level normalized match** (1 if the whole invoice matched, else 0).
Lower is better; 0.25 is what always guessing "0.5" scores. Analogy: a
weather forecaster who says "90% chance of rain" is penalized a little when
it rains and a lot when it doesn't.

Worked miniature: confidences 1.0, 0.0, 0.5, 0.8 with outcomes right, wrong,
right, wrong → (0 + 0 + 0.25 + 0.64) ÷ 4 = **0.2225**.

**Calibration bins and ECE.** Confidences are grouped into ten fixed bins
(0–0.1, …, 0.9–1.0, last bin right-closed). In each bin we compare the mean
confidence to the observed match rate. Expected calibration error is the
count-weighted average gap. Worked miniature: one record at 0.05 that is
wrong (gap 0.05) plus two at 0.95 of which one is right (gap 0.45) →
ECE = (1×0.05 + 2×0.45) ÷ 3 ≈ **0.3167**. Empty bins report "no data," never
a fabricated zero.

**Selective risk (coverage versus accuracy).** For each threshold *t*:
auto-accept records with confidence ≥ *t*, send the rest to a human.
*Coverage* = share auto-accepted; *risk* = error rate among the auto-accepted.
A record with **no confidence value, no expected evidence, or a missing
expected prediction can never be auto-accepted** — incomplete evidence routes
to review regardless of confidence.

**Cost-sensitive threshold sweep.** Expected cost per invoice at threshold
*t* = (reviews × review_cost + wrong auto-accepts × error_cost) ÷ N. Both
costs are **caller-supplied, finite, non-negative business inputs** — the
harness hard-codes no price. Worked miniature (review 1, error 10, four invoices): at t=0, one
review + one wrong accept → (1 + 10)/4 = 2.75; at t=0.75, two reviews and no
wrong accepts → 0.5. The sweep is labeled decision support: it informs a
human business choice offline; it never sets a runtime threshold by itself.

**Latency/token summaries.** Count, min, max, mean, median, and nearest-rank
p95 over `latency_ms`; totals and means over token counts, with missing
values counted rather than zeroed. Optional cost estimates multiply token
totals by caller-supplied finite, non-negative per-1k prices.

## 4. Where data science belongs in ProofLoop

ProofLoop's runtime is deliberately deterministic: the LLM only reads
untrusted text into a strict schema, and the verdict, disposition, and HITL
routing are pure functions. Data science lives **around** that runtime, not
inside it:

- *before* deployment: measuring extraction quality per document category;
- *beside* operations: watching whether confidence is calibrated and whether
  quality drifts by source or category;
- *feeding governance*: giving the product owner evidence for a human
  decision about the review threshold, model choice, or prompt change.

Analogy: the evaluation layer is the flight-data recorder and wind-tunnel
program; the deterministic evaluator is the flight-control law. The analysis
improves the next design review — it never grabs the stick mid-flight.

## 5. Why the runtime verdict stays deterministic

A compliance verdict must be **auditable and reproducible**: the same
evidence must always yield the same verdict, and an auditor must be able to
recompute it. A statistical score cannot promise that; a model-reported
confidence certainly cannot. So no evaluation output, metric, threshold
recommendation, or ML score can create or modify GREEN/AMBER/RED, approve an
invoice, release a payment, bypass HITL, or alter evidence freshness. This is
enforced structurally: `proofloop.evaluation` imports no runtime package, no
runtime package imports it (both directions are locked by tests), and its
report never even emits runtime-verdict vocabulary. The SAM packaging helper
also excludes `proofloop.evaluation`, Python caches, and bytecode from both
Lambda artifacts; built-artifact verification enforces that boundary.

## 6. The normalization policy (exact and conservative)

Text: Unicode NFKC → collapse whitespace runs to one space → strip →
casefold. Nothing else — "Acme  GMBH" equals "acme gmbh", but no punctuation
stripping or transliteration that could merge genuinely different values.

Numbers: only plain decimal strings parse (optional sign, digits, at most one
decimal point). Currency symbols and thousands separators are **refused, not
stripped**, because "1,234" versus "1.234" is locale-ambiguous and a wrong
guess could hide a real financial error. Unparseable values are excluded and
counted, never guessed.

## 7. Calibration versus confidence

A model can output a *confidence* number with any request — that does not
make it a probability. Confidence is **calibrated** only when, over many
cases, "0.8" events actually happen about 80% of the time. Until the Brier
score and calibration bins say so on trustworthy labels, ProofLoop treats
`model_reported_confidence` as an uncalibrated signal: it may *support*
analysis but never *declare* correctness. That is the same rule as the
runtime's "probabilistic signals can support but never declare GREEN."

## 8. Threshold selection is a business-cost decision

There is no universal "right" confidence threshold. The best threshold
depends on what a human review costs versus what a wrong auto-accepted
invoice costs — numbers only the business knows. The sweep makes that
trade-off explicit and lets the owner choose; it also refuses the classic
statistical mistake: a threshold **tuned** on one split may not have its
final performance **reported** from that same split. The report flags this
(`split_misuse`) and withholds the claim.

## 9. Three kinds of drift (and why we separate them)

- **Data drift:** incoming documents change (new vendor layouts, new
  languages, scan quality). Detect via per-category/source tags and rising
  numeric-prediction missing or unparseable counts.
- **Quality drift:** the same kinds of documents start scoring worse (match
  rates fall, numeric errors grow) — the model/prompt is degrading relative
  to the workload.
- **Model-contract drift:** the provider/prompt/configuration identity
  changes (`provider_config_id`, `prompt_config_id`). Runtime ProofLoop
  treats this as provenance mismatch (AMBER, `OBSOLETE_PROVENANCE`); the
  evaluation layer records it so results are never blended across contracts.

Separating them matters because the fixes differ: data drift needs new
labeled examples; quality drift needs prompt/model work; contract drift needs
re-evaluation before trusting old numbers.

## 10. Dataset provenance and leakage

Every record declares its provenance — `SYNTHETIC`, `PUBLIC`, or
`DEIDENTIFIED_CUSTOMER` — and its split — `DEVELOPMENT` (tune), `VALIDATION`
(select), `HOLDOUT` (report once). The dataset validator **refuses** the same
record id in two splits (leakage) and duplicate ids within one split. Why it
matters: a model evaluated on data it was tuned against looks better than it
is; leakage silently converts an honest estimate into marketing.

## 11. What can and cannot currently be claimed

**Can be claimed now:**
- The evaluation harness exists, is deterministic, is fully unit-tested, and
  is structurally isolated from the runtime verdict path and Lambda artifacts.
- All metrics behave correctly on hand-computed miniature examples and on
  synthetic fixtures.

**Cannot be claimed (and the report itself says so):**
- Any production accuracy, calibration, latency, or cost figure — current
  fixtures are synthetic (`claim_boundary: SYNTHETIC_ONLY`).
- Any model-superiority conclusion — there has been no real Bedrock request,
  let alone a statistically meaningful sample.
- Any minimum sample size for production readiness — the report states exact
  n and refuses to invent a threshold.
- Any influence on runtime compliance — structurally impossible, verified by
  tests in both import directions.

## 12. How a future de-identified customer evaluation would run safely

1. **Authorization first:** written product-owner approval naming the data
   source, retention window, and deletion date.
2. **De-identification before ingestion:** PII removal happens upstream. The
   record schema stores only bounded allow-listed invoice scalar values and
   rejects common PII, credential, prompt-marker, control-character, and
   arbitrary-payload shapes as a conservative backstop. This is not a DLP
   system and does not replace an approved enterprise de-identification step.
3. **Provenance labeling:** records enter as `DEIDENTIFIED_CUSTOMER` with
   category/difficulty/source tags, split assignment fixed **before** any
   metric is run, holdout untouched until the final report.
4. **Offline execution:** the CLI runs on local files; no network, no cloud
   call, no runtime state.
5. **Claim discipline:** results state n, provenance, and split; calibration
   claims come only from validation/holdout; the tuning/reporting split rule
   is enforced by the tool, not by good intentions.
6. **Runtime unchanged:** whatever the evaluation finds, changing a
   production threshold or prompt remains a separately reviewed human change
   with new runtime evidence required before GREEN.
