# Data-Science Interview Guide — ProofLoop Offline Evaluation Layer

*How to explain and defend every design decision in the evaluation layer.
Companion to `docs/submission/DATA_SCIENCE_EVALUATION.md` (the concepts) —
this file is the defense script. Everything here is true of branch
`claude/offline-data-science-evaluation`.*

---

## The 30-second answer

> "I added an offline data-science evaluation layer for the invoice
> extractor: versioned bounded records, deterministic metrics — match rates,
> exact-decimal numeric errors, Brier score, calibration bins, ECE, selective
> risk, and a cost-based threshold sweep — with JSON and Markdown reports.
> It's structurally fenced out of the runtime: the evaluation package and the
> runtime packages cannot import each other, which tests enforce in both
> directions. So I can measure and improve the model without ever letting a
> statistic touch the deterministic GREEN/AMBER/RED verdict."

## The design decisions and their defense

**Q: Why is the evaluation offline instead of a live dashboard metric?**
Because the runtime promise is auditability: same evidence, same verdict,
recomputable by an auditor. A live statistical feed inside the verdict path
would break that promise. Offline evaluation gives the same insight with zero
runtime risk. If asked "could you wire it in later?" — the honest answer is
that its outputs could *inform a human* change request, but the architecture
deliberately has no code path for it to act on the runtime, and tests would
fail if someone added one.

**Q: How do you *prove* the isolation, rather than promise it?**
Three tests: (1) AST scan — no file in `proofloop.evaluation` imports any
runtime package, banned SDK, or runtime verdict type; (2) reverse AST scan —
no runtime file imports `proofloop.evaluation`; (3) a clean-subprocess import
probe — importing the whole evaluation package pulls zero runtime modules
into `sys.modules`. Plus the report writer is checked to never emit runtime
verdict vocabulary, so its output can't even be spliced into a compliance
record convincingly.

**Q: Why Decimal everywhere instead of floats/NumPy?**
Money. `0.1 + 0.2 != 0.3` in binary floats, and an evaluation of *financial*
extraction that itself rounds wrongly would be self-defeating. Decimal also
makes output byte-deterministic, which the reproducibility contract needs.
NumPy would add a heavy dependency for arithmetic the standard library does
exactly; the project rule is dependency-light unless proven necessary.

**Q: Why is the Brier target invoice-level match instead of per-field?**
The model reports one confidence per invoice, so the honest binary target is
the thing that confidence is about: "was this whole extraction right?" A
per-field target would need per-field confidences the model doesn't emit.
This is documented in every calibration result's limitations.

**Q: What happens with missing confidence values?**
They're excluded and counted (`excluded_missing`), never coerced to zero.
Coercing to zero would make an uncertain model look pessimistic-but-
calibrated — a silent lie. Same principle as the runtime's "silence never
manufactures RED": missing data is *unknown*, not a value.

**Q: Zero denominators?**
Three distinct cases, each explicit: empty input → `INSUFFICIENT_EVIDENCE`
with value `None`; relative error with expected value 0 → excluded and
counted in `excluded_zero_denominator`; empty calibration bins → `None`
rates, never a fabricated 0.

**Q: Why such a strict normalization policy?**
Every normalization step is a claim that two different strings mean the same
thing. NFKC + whitespace + casefold are safe for that claim; stripping "$" or
"," is not, because "1,234" vs "1.234" is locale-ambiguous and merging them
could hide a thousand-fold financial error. Conservative normalization means
match rates might *understate* quality — the safe direction to be wrong in.

**Q: How do you avoid the classic tuning/reporting mistake?**
Splits are first-class in the schema. The dataset validator refuses the same
record in two splits (leakage). The threshold sweep runs on the tuning split
only, and if the configured reporting split equals the tuning split the
report sets `split_misuse: true` and withholds the tuned-threshold
performance claim — the tool enforces the discipline, not the author.

**Q: What would you claim from the current numbers?**
Nothing about production. Current fixtures are synthetic, so the report's own
`claim_boundary` is `SYNTHETIC_ONLY` and its unsupported-claims section says
no production accuracy or calibration claim is supported. What I *can* claim:
the harness is correct (hand-computed examples), deterministic, and isolated.

**Q: How would you get real numbers?**
The documented path in `DATA_SCIENCE_EVALUATION.md` §12: authorized,
de-identified customer data, provenance-labeled, split before measurement,
holdout touched once, run offline. Then Brier/ECE on validation tells us if
confidence is usable, and the cost sweep with the customer's actual review
and error costs gives the owner a defensible threshold proposal.

**Q: Where does the cost model come from?**
The caller. Both the review/error costs and token prices are inputs — nothing
is hard-coded — because a hard-coded price is stale the day it ships and a
hard-coded cost ratio smuggles a business decision into library code. Inputs
must be finite and non-negative; unjudgeable or incomplete records route to
review rather than becoming free auto-accepts.

## Vocabulary to use precisely

- **Accuracy** — only with trustworthy labels; on synthetic fixtures say
  "fixture agreement" or "match rate."
- **Confidence vs. probability** — confidence is a model's self-report;
  probability requires demonstrated calibration.
- **Calibration** — the property that stated confidence matches observed
  frequency; measured by bins/ECE, summarized by Brier.
- **Coverage / selective risk** — how much you automate versus how wrong the
  automated part is.
- **Descriptive vs. calibration vs. decision-support** — every metric result
  carries its `kind` so nobody mistakes a description for a recommendation.

## Boundaries to state out loud (do-not-overclaim)

- No production accuracy, calibration, latency, or cost figure exists — no
  real Bedrock call has been made.
- The evaluation layer does not run in the Lambda path and is excluded from
  both built Lambda artifacts. The SAM template and runtime handlers remain
  unchanged; only the bounded packaging helper changed.
- The record allow-list and PII/credential/content guards are structural
  backstops, not enterprise DLP; inputs still require approved upstream
  de-identification.
- Model-reported confidence remains uncalibrated until real labeled data
  says otherwise.
