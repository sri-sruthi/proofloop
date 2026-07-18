# Databricks Guides — Harvest for the Vigil Write-up & Interview

*Read Jul 16 from your Drive: "State of AI Agents 2026" (Databricks telemetry, 20k+ orgs,
60%+ of Fortune 500) and "The Big Book of GenAI" (governance + evaluation chapters). These
are enterprise-grade sources you can CITE in the PDF write-up and quote in the AI interview.
Everything below is a real figure/claim from those docs.*

## A0. THE headline stat for Vigil (from "Making AI Deliver," 2026 benchmarking report)
*This report — an Economist-Impact-style benchmarking study in your Drive — is the single
strongest business-case source for Vigil, because Vigil IS a post-deployment monitor.*
- **"Governance thins out where it matters most. About three in five firms review AI
  systems during development and before deployment. Fewer than two in five continue that
  oversight after a system goes live — the stage where AI models drift, data shifts and
  edge cases multiply."** → i.e. **~60% govern pre-deploy, <40% keep governing in
  production.** That gap is precisely where cross-session attacks live. Lead the write-up
  with this.
- **"Governance that covers only the approval stage and thins out after deployment creates
  a false sense of security."**
- **"A governance framework that does not follow the technology into production is a
  framework that governs only the version of the system that no longer exists."**
- **"Firms with proper safeguards, such as real-time monitoring, suffered a third fewer
  failures."** → quantifies the ROI of exactly what Vigil provides (runtime monitoring).
- Nasdaq exemplar: "every AI agent carries an identifier, holds defined authorities and is
  fitted with observability tools and a kill switch." → Vigil's per-user risk + alert is
  the missing *cross-session* observability alongside these per-agent controls.
- "Fewer than half formally require AI outcome metrics to inform updates to their rules" →
  the feedback loop is missing; Vigil's calibration + alert-review loop supplies one.
- Supporting (MITTR/Databricks 2025 CIO survey, also in Drive): only **19%** of orgs have
  started using agentic AI (46% among data "high achievers"); **38%** cite establishing
  clear governance/security as the top agentic challenge, **34%** regulatory/compliance
  risk. "Machines taking actions puts an extra onus on data and AI leaders to ensure clear
  and robust data governance and security."

## A. Stats that make the business case (put these in the write-up intro)
- **Governance is the #1 production lever, quantified:** companies using AI governance put
  **12× more** AI projects into production; governance usage grew **7× since Jan 2025**.
  (This single stat justifies the entire Aivar problem set — and Vigil sits in it.)
- **Evaluation is the #2 lever:** teams using eval tools get **~6× more** projects to prod.
  → We adopt this directly: Vigil ships with an eval harness that measures detector
  precision/recall on the simulated cohort. Not decoration — it's the thing that separates
  production from prototype, per Databricks' own data.
- **95% of GenAI pilots fail to reach production** (MIT NANDA, cited by Databricks). The
  three blockers named: **Quality, Governance, Cost.** Vigil is Governance; our
  production-thinking ledger explicitly addresses Cost (token budget) and Quality (FPR).
- **Only 19% of orgs have deployed agents** — the market is early; governance tooling is
  being bought *now* (7× growth). Timely, not crowded-at-the-app-layer.
- **Customer support is the anchor use case:** 40% of top AI use cases are customer
  experience/engagement; support inquiry classification & routing is a named top use case.
  → Justifies our demo workload (a support agent) as the realistic thing enterprises run
  and attackers probe. Also: Klarna-class (from web research) = the same use case.
- **96% of requests are real-time**, 78% of companies use 2+ LLM model families. → Vigil
  must be provider-agnostic (consume events from any model) and low-latency/non-blocking.

## B. ⚠️ CORRECTION — a false claim removed (Jul 17)
An earlier draft of this section claimed "Databricks/MLflow operates per-request/per-trace
and cannot ask cross-session user questions, so per-user cross-session correlation is
structural whitespace." **That is FALSE and must never appear in the write-up.** MLflow
explicitly supports attaching `mlflow.trace.user` + session IDs and querying ONE user's
traces across a time window (e.g. 7 days) to compute "total interactions / unique sessions
/ daily activity / error rate" — i.e. per-user, cross-session analysis out of the box
(https://docs.databricks.com/aws/en/mlflow3/genai/tracing/add-context-to-traces-tutorial).
AWS AgentCore Optimization likewise surfaces failure/intent/trajectory insights "across
hundreds of sessions." So cross-session analysis is NOT whitespace. (This false claim was a
key prop of the earlier Vigil recommendation; its collapse is part of why the final pick
moved to scoped PS-6.2 ProofLoop — see `CROSS_EVALUATION…FINAL_VERDICT` Round 2.)

## B2. How this Databricks material actually helps ProofLoop (the chosen PS-6.2)
Reframed for ProofLoop, the same governance stack is the market-comparison anchor — and
honestly, not as fictional whitespace:
- **AI Gateway** (rate limit, PII mask, safety filter, fallback) and **MLflow Tracing**
  (per-trace observability, judges/scorers, cost/latency) tell you a control was CONFIGURED
  and show you traffic. **What no mainstream stack does is actively PROVE a specific control
  is still executing on the live path right now, and refuse a false "green" when evidence
  is missing/stale.** That is ProofLoop's narrow, defensible distinction (active canaries +
  explicit UNKNOWN state + fresh-evidence-before-recovery). State it as a distinction, never
  as "nobody monitors production" (ServiceNow AI Control Tower, IBM watsonx.governance,
  OneTrust, AgentCore Observability all do — name them, then draw the specific line).
- The §A0 post-deployment governance-gap stats are a DIRECT business case for PS-6.2
  Runtime-to-Compliance: ~60% govern pre-deploy, <40% after go-live; "real-time monitoring →
  a third fewer failures"; governance-tooling → 12× more to production. ProofLoop is the
  "keep governing after go-live" layer those numbers call for.

## C. Techniques to borrow (and name-drop) so Vigil reads as industry-fluent
- **Traces & spans as the event unit** (MLflow vocabulary). Frame Vigil's SessionEvent as a
  distilled trace: tool calls, outcomes, guardrail verdicts per turn. Speak their language.
- **LLM-judge / scorers pattern**: use an LLM-as-judge (Haiku) to label ambiguous requests
  by capability tier and to write the alert card — cite this as the "scorer" pattern, and
  calibrate it against a small labelled set (their "custom judge calibration" / SME loop).
- **Synthetic scenario generation** for baselines/eval (Agent Bricks does exactly this) —
  legitimises our simulator generating the benign + adversarial cohorts. PS-4.3 requires
  simulated traffic anyway; now it's a named industry practice, not a shortcut.
- **Inference tables / payload logging → drift monitoring** (Lakehouse Monitoring). Our
  risk-decay + threshold-recalibration is the same idea applied to adversarial drift.
- **Eval-run vs eval-dataset discipline**: version the simulated cohort as a fixed eval
  dataset; report a single eval-run table (precision/recall/FPR per archetype). This is the
  "6× to production" practice made concrete.

## D. Interview ammunition (the gated AI round)
The doc hands you fluent, current talking points on: MLflow tracing/observability, LLM
judges vs scorers, TAO (test-time adaptive optimization), ALHF (agent learning from human
feedback — 32 feedback records took adherence 11.7%→~80%), OBO auth + ABAC, provider-
agnostic model serving, the Quality/Governance/Cost framing. Skim these before the round —
they're the exact vocabulary an ex-AWS/enterprise panel uses.

## E. Free course they name (relevant, optional, post-submission)
"Governing AI Agents" — DeepLearning.ai, available on **Databricks Free Edition** (not
Coursera, but free). Good for the interview window. Also: Generative AI Fundamentals
(Databricks Academy).

## Drive docs — mining status (all 8 assessed; nothing left open)
MINED end-to-end and folded into this doc:
- `State-of-AI-Agents-2026-Final.pdf` — §A (12×-governance, 6×-eval, 95% pilots fail, support use case).
- `2026-03-eb-big-book-of-genai-ss-200225.pdf` — §B/C/D (AI Gateway per-request, MLflow per-trace, judges/scorers, TAO, ALHF).
- `making-ai-deliver-2026-report-new.pdf` — §A0 (the post-deployment governance-gap stats — the headline material).
- `mittr-databricks-data-and-ai-2025-report.pdf` — §A0 (CIO survey: 19% agentic adoption, 38% governance challenge).

ASSESSED, deliberately NOT folded in (genuinely off-thesis for Vigil — noting so no thread is left dangling):
- `Databricks_..._Compact_Guide_To_RAG-2nd-edition.pdf` — RAG pipeline mechanics; only relevant if we add RAG (we don't in the core).
- `hands-on-guide-apps-databricks.pdf` — Lakebase/Apps + agent conversational memory; not Vigil's problem.
- `big-book-data-engineering.pdf` — data-pipeline observability/lineage; adjacent vocabulary only, no Vigil-specific stat.
- `ebook_mit-cio-generative-ai-report.pdf` — overlaps the MITTR CIO survey already mined in §A0; no additional distinct figure.

*Research complete — Jul 16. No open Databricks/Drive threads remain.*
--- END OF DOCUMENT ---
