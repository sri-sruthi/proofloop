# Clarity — The Decision Path Auditor
## Aivar Task · Full Project Plan (Option: PS-7.1, Unit 7 — Audit Trails & Explainability)
*Drafted 2026-07-13 · non-cybersecurity · best fit for your NLP / LLM-evaluation background*

> Compare with the other PROJECT_PLAN_*.md files and DECISION_BRIEF /
> MARKET_AND_PS_RECONSIDERATION. Shared production apparatus, AWS stack, cost, and
> deliverable spec are in PROJECT_PLAN.md §; only the deltas are spelled out here.

---

## 1. The Decision
**Build PS-7.1: a Decision Path Auditor** — instrument an agent so that for any
consequential output you can reconstruct the *full causal chain* (input → context
retrieved → tools called → reasoning → decision), **generate a plain-English explanation
for the affected person**, and **auto-redact PII** before storage. Deployed on AWS,
governing a real Claude/Bedrock agent.

### Why this fits YOU
- **NLP + LLM + evaluation = your clinical-LLM project, exactly.** The core deliverable
  (LLM-generated explanation + judging its accuracy/readability) is the same muscle you
  used benchmarking LLMs on NBME/Synthea.
- **PII redaction = your clinical NER work** (medical text, structured extraction).
- **Explainability is a beloved, high-status DS topic** — model interpretability — and
  it's **zero cybersecurity**. You'll speak about it with genuine interest.

### Why it's important to AWS + Aivar
- **McKinsey 2026 names lack of trace-level visibility/explainability the #1 reason agent
  rollouts stall.** EU AI Act Art. 13 requires transparency for high-risk AI.
- AWS Well-Architected Agentic-AI Lens: "make every agent action observable and traceable
  end-to-end." Aivar = "Governed Agentic AI Stack."

### Differentiation (honest, defensible — you don't need to beat everyone)
Existing tools (Fiddler, Braintrust, LangSmith, HydraDB, miniOrange) reconstruct traces
**for developers**. Your edge: **explanation for the *affected person and the regulator*,
not the engineer** — a plain-language decision narrative + PII-safe storage + a draft
**regulatory challenge response**. That "human/regulator-facing explainability" is a real
gap and it's NLP-heavy (your strength). Say clearly what you DON'T do (not a full APM/
observability suite) — that honesty scores with ex-AWS reviewers.

---

## 2. Requirements & success criteria (each → a named test + demo scene)
Build: (a) instrumented agent wrapper logging every step; (b) decision-path reconstructor
by session ID → structured timeline; (c) LLM decision-summary generator (plain English);
(d) PII auto-redaction before persistence.
Success: 1) 3-step task (retrieve→reason→decide) reconstructed with all intermediate
steps; 2) summary accurate + readable by a non-technical reviewer; 3) PII in tool
responses redacted in the stored record; 4) path queryable by session/user/time.
Bonus: **challenge-response generator** — given a decision path, draft a reply to a
regulatory challenge citing the specific data considered.

---

## 3. Architecture
```
 User ── task ──► Agent (Claude/Bedrock, Agent SDK) ──► MCP tools (retrieve, lookup, decide)
                        │  every step emitted
                        ▼
              ┌───────────────────────────────────────────────┐
              │  CLARITY service (FastAPI on AWS Lambda)        │
              │  ┌───────────────┐   ┌───────────────────────┐ │
              │  │ Step logger    │──►│ PII redactor (NER +   │ │
              │  │ (input, tools, │   │ regex) BEFORE storage │ │
              │  │ params, reason,│   └───────────┬───────────┘ │
              │  │ output)        │               ▼             │
              │  └───────────────┘   ┌───────────────────────┐ │
              │  ┌───────────────┐   │ Path reconstructor →   │ │
              │  │ LLM summarizer │◄──│ structured timeline    │ │
              │  │ (plain English)│   └───────────────────────┘ │
              │  └───────┬───────┘   ┌───────────────────────┐ │
              │          └──────────►│ Challenge-response gen │ │
              │                      └───────────────────────┘ │
              └───────────┬───────────────────┬───────────────┘
                          ▼                    ▼
                    DynamoDB (redacted     S3 (long-form
                    paths, token map,      explanation docs)
                    queryable indexes)     CloudWatch / OTel traces
                          │
                          ▼
                    Reviewer UI: timeline + plain-English summary + "why" per step
```

## 4. Component decisions (deltas)
- **PII redaction:** open-source NER (e.g., a HuggingFace token classifier) + regex, with
  a **secure token↔PII map** (DynamoDB, access-controlled) so redaction is reversible for
  authorized roles. This is your clinical-NER skill applied.
- **Summary quality = a DS deliverable:** define a rubric (faithfulness to the path,
  completeness, readability) and **evaluate the LLM summaries** (LLM-as-judge + a small
  human-rated set) — your evaluation methodology, documented.
- **Redaction-before-persist** ordering is a governance guarantee (PII never hits disk raw).
- Rest of stack (Lambda, DynamoDB, S3, API Gateway, CloudWatch, SAM IaC, GitHub Actions
  CI/CD, OTel) = shared apparatus.

## 5. Innovations
1. **Affected-person + regulator-facing explanations** (not developer traces) — the market gap.
2. **Redaction-before-persistence + reversible token map** — PII-safe audit by construction.
3. **Summary-quality evaluation harness** (faithfulness/readability rubric) — your DS rigor
   applied to LLM output, which most builders skip.
4. **Challenge-response generator** (the bonus) — a draft regulatory reply grounded in the
   exact data considered.

## 6. Coverage map
Agentic AI (instrumented agent loop) · MCP (tools) · **RAG (native:** the "retrieve" step
is a real RAG lookup whose contribution to the decision you trace) · LLM + prompt
engineering (the summarizer) · **NLP/DS core** (redaction NER + summary evaluation) ·
memory (session-indexed paths) · monitoring/OTel · error handling · **AWS + DevOps**
(deploy + IaC + CI/CD) · explainability (the whole point).

## 7. Customer motto · 8. Ex-AWS reviewers · 9. Cost · 10. Deliverables · 11. Build seq
Same framework as PROJECT_PLAN.md, tailored:
- **Customer:** the *affected end-user* deserves to know why a decision was made (persona:
  compliance officer + affected customer). Redaction protects the customer's PII.
- **Reviewers:** Well-Architected mapping; honest "we're not an APM suite" scope; summary-
  eval metrics; market comparison (Fiddler/Braintrust do dev-traces; we do human-facing).
- **Cost:** ~$0/mo free tier + ~$3–5 Bedrock/Anthropic credit (summaries are cheap Haiku).
- **Deliverables:** PDF (with the required diagrams), 5–8 min video (demo first: a decision
  → reconstructed timeline → plain-English explanation → PII redacted → challenge draft),
  repo + README + one-command deploy.
- **Build (Wed-night→Sat):** P1 instrumented agent + step logging → P2 reconstructor +
  DynamoDB → P3 LLM summarizer + redaction → P4 AWS deploy (SAM) → P5 reviewer UI +
  challenge-response → P6 eval harness, docs, video.

## 12. Sources / differentiation
McKinsey 2026 (explainability = #1 rollout blocker); EU AI Act Art. 13; AWS Agentic AI
Lens; market: Fiddler, Braintrust, Atlan, HydraDB, miniOrange (dev-facing traces). Links
in MARKET_AND_PS_RECONSIDERATION.md.
