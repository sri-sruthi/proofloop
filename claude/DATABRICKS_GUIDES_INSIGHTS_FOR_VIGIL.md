# Databricks Guides → What Vigil Uses (distilled Jul 16, 2026)

*Source: Sri's Google Drive. Read END-TO-END: `State-of-AI-Agents-2026-Final.pdf` (full),
`2026-03-eb-big-book-of-genai` chapters 4–5 (evaluation + governance — the relevant ones;
ch. 1–3 are agent-building/RAG basics). Skimmed via snippets: MIT TR data+AI report.
Skipped as off-topic for this build: RAG compact guide, Lakebase/Apps guide, big-book
data engineering, MIT CIO report, making-ai-deliver.*

## A. Quotable evidence for the PDF write-up (cite: Databricks State of AI Agents 2026 —
telemetry from 20,000+ orgs incl. 60% of Fortune 500)
- **Companies actively using AI governance put 12x more AI projects into production.**
  Governance investment grew **7x in nine months** (AI Gateway usage since Jan 2025).
  → Governance isn't compliance overhead; it's the production enabler. Opening stat.
- **Companies using evaluation tools get ~6x more AI projects into production.**
  → Justifies Vigil's calibration/eval-first design (measured FPR, published distributions).
- **40% of enterprise AI use cases are customer experience** (support, advocacy,
  onboarding). → Validates our demo workload: a customer-support agent is THE
  representative governed system, not a toy.
- **96% of inference is real-time** → detection must be streaming/low-latency, not batch.
  Vigil's per-event scoring design matches how enterprises actually serve.
- Multi-agent systems grew **327% in four months**; 78% of companies run 2+ model
  families → per-user correlation must be provider- and agent-agnostic (our event schema
  is: any guardrail, any model, one stream per user identity).
- **95% of GenAI pilots fail to reach production** (MIT NANDA, cited in Big Book) — the
  "reliability wall": quality, governance, cost. Our write-up frames Vigil as attacking
  the governance blocker with a cost-bounded design (the other two blockers).
- MIT TR (2025, w/ Databricks): 67% of orgs use AI tools but **only 19% have deployed
  agents** — governance gap is the #1 cited brake ("avoiding agent chaos").
- Economist Impact 2024: **40% of orgs say their AI governance program is insufficient.**

## B. The killer positioning line the Big Book hands us
Databricks' flagship governance stack = Unity Catalog (assets) + **AI Gateway** (central
proxy: rate limits per user/endpoint, PII masking, safety filtering, payload logging,
fallbacks) + **MLflow Tracing** (per-trace spans) + LLM judges sampling production traffic
for quality drift. **Every control evaluates the current request or trace in isolation.**
Same for AWS AgentCore Policy (Cedar per tool-call). So, for the market-comparison section:

> "From AWS AgentCore Policy to Databricks AI Gateway, every shipping governance control
> plane makes a stateless decision about the current request. None accumulates evidence
> about the REQUESTER. A patient adversary never loses a single request — they win across
> fifty. Vigil is the missing stateful layer: it consumes the guardrail outcomes these
> platforms already emit and answers the question none of them ask."

Also honest related-work note: Databricks' "governance + evaluations are symbiotic —
evaluations monitor agent behavior, enabling governance to adapt in real time" is the
closest philosophical neighbor to Vigil; but their monitoring targets agent QUALITY
drift, not user adversarial patterns. Distinguish quality-monitoring vs threat-monitoring.

## C. Design decisions Vigil adopts from these guides
1. **Event schema mirrors trace/span semantics** (MLflow/OTel style: session_id, user_id,
   span attributes incl. guardrail outcome + rule id). Write-up cla