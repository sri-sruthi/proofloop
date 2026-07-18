# Sentinel — Prompt Injection Behavioral Detector
## Aivar Innovations AI Governance Task · Full Project Plan (Option B)
**Problem statement: PS-3.2 "Prompt Injection Behavioral Detector" (Unit 3 — Runtime Guardrails)**
*Plan drafted 2026-07-12 · Author: Sri Sruthi (with Claude Code)*

> Read this alongside `PROJECT_PLAN.md` (the Agent WAF / PS-5.1 option) and
> `DECISION_BRIEF.md` (side-by-side comparison). This is the option that maps most
> directly onto Sri Sruthi's existing resume.

---

## 1. The Decision

**Build PS-3.2: a behavioral anomaly detector for prompt injection** that detects
*successful* injections by observing what an agent **does next** — its tool-call
sequence and parameter patterns — not by inspecting prompt text. Deployed on **AWS free
tier**, wrapped around **real Claude-powered agents** using MCP tools.

### Why PS-3.2 is the strongest fit for *this* candidate

This problem statement is, structurally, **the IoT Intrusion Detection project retargeted
from network traffic to agent behavior.** Every hard part has already been done once:

| PS-3.2 requirement | Your resume already proves it |
|---|---|
| Establish a behavioral **baseline** from 20–30 normal runs | IoT-IDS: built behavioral traffic baselines over 39 shared NetFlow features |
| **Anomaly scorer** comparing new runs to baseline | IoT-IDS: cross-domain anomaly detection, F1 0.999 → 0.387 → 0.722 with adaptation |
| **Calibration** — 2/20 normal runs score elevated but below threshold (not a binary check) | Deepfake challenge: logistic-regression **calibration** of predictions; Clinical LLM eval: matching-strictness **sensitivity analysis** (F1 shifted up to 0.127) — you already think in thresholds and false-positive tradeoffs |
| Instrument a **real agent** + simulate injected tool outputs | Newsletter multi-agent orchestrator: LLM scoring pipeline, real API tool calls, scheduled runs |
| Serve it, deploy it, dashboard it | Video-Intelligence project: FastAPI + Docker + Render deploy |

**Consequence for the interview:** the deepest questions a senior ex-AWS reviewer can
ask — *"How did you set the threshold? What's your false-positive rate? How do you know
the baseline generalizes? What about distribution shift?"* — land exactly on things you
have already published three projects about. You get **stronger** under scrutiny, not
weaker. That is the entire game.

### Why it's also on-trend and high-impact

- **Indirect / behavioral prompt injection is OWASP's #1 LLM risk** and the single
  hardest unsolved problem in agent security in 2026.
- The doc's own framing — *"current tools miss these because they look at prompt syntax,
  not at whether the agent's behaviour changed"* — means you are building something the
  market genuinely lacks (most commercial guardrails are still text classifiers).
- Pairs with the same 2026 trend stack as the WAF: MCP, Claude Agent SDK, AWS,
  OpenTelemetry GenAI conventions, EU AI Act (enforcement begins August 2026).

### The video narrative no other candidate can tell

> *"In my IoT research I showed intrusion detectors collapse from F1 0.999 to 0.387
> across domains, and I rebuilt them with domain adaptation and self-training. AI agents
> are the new network traffic — so I applied the same behavioral-baseline methodology to
> detect prompt injection by what the agent **does**, not what the prompt **says**."*

This is a story about **you**, not about a tool that generated code.

---

## 2. What the evaluators demand (unchanged across options)

- Production-ready, **deployed on AWS**, governing agents also on AWS (beats localhost).
- **Concurrent requests, persisted state, usable API.**
- **Logging, error handling, health check.**
- **At least one real LLM provider** (not mocked).
- Extra points: deployment quality, integration breadth, plug-in-ability.

**Submission (hard rules):** zip via Google Form, publicly accessible URL, **no public
GitHub/LinkedIn/social**; 5–8 min video with **demo first**; PDF with architecture
diagrams + market comparison; code + README + automated deploy scripts.

**PS-3.2 success criteria (each → a named test + a demo scene):**
1. Baseline correctly established from ≥20 normal runs.
2. All three injected runs produce anomaly scores significantly above the normal range.
3. **Calibration proof:** ≥2 of 20 normal runs score higher but stay below the flagging
   threshold — demonstrating calibration, not a binary check.
4. Detection happens **within one agent turn** of the injection taking effect.
5. **Bonus:** suspicion accumulator — anomaly accumulates across turns in a session; a
   persistent low-level anomaly is flagged even if no single turn crosses the threshold.

---

## 3. Architecture

```
                        ┌─────────────────────────── AWS ────────────────────────────┐
 Demo driver /          │                                                            │
 scenario runner        │   ┌──────────────┐   tool calls (MCP)   ┌───────────────┐  │
      │                 │   │ Instrumented  │ ───────────────────► │  Mock tools + │  │
      ▼                 │   │ Agent (Claude │                     │  POISONED tool │  │
 ┌──────────┐  emit     │   │ Agent SDK,    │ ◄─────────────────── │  outputs      │  │
 │ 50 normal │  events   │   │ Haiku 4.5)    │   tool responses    └───────────────┘  │
 │ + 3 inj.  │──────────►│   └──────┬───────┘                                         │
 │ scenarios │           │          │ behavioral event stream                        │
 └──────────┘           │          ▼ (tool name, order, params, timing)              │
                        │   ┌────────────────────────────────────────────┐          │
                        │   │  SENTINEL detection service (FastAPI/Lambda) │          │
                        │   │  ┌────────────┐  ┌───────────────────────┐  │          │
                        │   │  │ Baseline    │  │ Anomaly scorer:        │  │          │
                        │   │  │ profiler    │─►│ • seq n-gram surprise  │  │          │
                        │   │  │ (fingerprint│  │ • tool-freq divergence │  │          │
                        │   │  │  store)     │  │ • param distribution   │  │          │
                        │   │  └────────────┘  │ • novel-tool flag       │  │          │
                        │   │                   └──────────┬────────────┘  │          │
                        │   │   suspicion accumulator ◄─────┘               │          │
                        │   └───────────┬───────────────────┬──────────────┘          │
                        │               ▼                   ▼                          │
                        │        DynamoDB (baseline,   Enforcement hook:               │
                        │        session scores,       score > threshold →             │
                        │        audit log)            SUSPEND session                 │
                        │               │                   │                          │
                        │               ▼                   ▼                          │
                        │        Live dashboard: score timeline per session,           │
                        │        normal vs injected distribution, flagged runs         │
                        └────────────────────────────────────────────────────────────┘
```

Flow: **agent runs a task → each tool call emits a behavioral event → Sentinel scores
the run against the stored baseline → if score crosses threshold, flag + suspend session
→ audit record → dashboard.** The injection lives in a **tool output** (retrieved
document / API response), never in the user prompt — that's the whole point.

### Component decisions

| Component | Choice | Rationale |
|---|---|---|
| Agent under observation | **Claude Agent SDK** agent on **Haiku 4.5**, connected to mock MCP tools (search, read-doc, send-email, db-query) | Real LLM provider requirement; real agent loop; MCP is the 2026 tool standard |
| Injection payloads | 3 crafted payloads embedded in **tool outputs** (poisoned retrieved doc, poisoned API response, poisoned file content) that redirect the agent's next actions | Exactly the "indirect injection" the doc asks for — not naive prompt-string attacks |
| Baseline profiler | Fingerprint over: tool-call frequency distribution, typical tool-call **sequences (n-grams)**, parameter value patterns, response length, data-access patterns | Directly your IoT-IDS methodology; produces an interpretable normal profile |
| Anomaly scorer | Composite score: sequence-surprise (n-gram / Markov transition probability) + frequency divergence (JS/KL) + parameter-distribution outlier + novel-tool indicator, combined into one calibrated score | Multiple weak signals fused = your deepfake "hybrid features + calibration" pattern |
| Threshold & calibration | Threshold set from the normal-run score distribution (e.g. mean + k·σ, or a chosen percentile); documented FPR/TPR tradeoff | The calibration success criterion is literally a DS deliverable — your strength |
| Detection service | **FastAPI** (async), deployed on **AWS Lambda + API Gateway** via SAM | Your existing FastAPI/Docker/deploy skill; matches evaluator's AWS scoring |
| State | **DynamoDB** — baseline fingerprint, per-session running scores, audit log | Free tier; concurrency + persistence proof |
| Enforcement hook | On threshold breach: mark session suspended in DynamoDB; subsequent agent turns rejected with a governance-hold message | Turns detection into governance (a mini-WAF moment); also the suspicion-accumulator bonus |
| Observability | Structured JSON logs shaped to **OpenTelemetry GenAI conventions** (`gen_ai.*`), CloudWatch, `/health`, `/metrics` | Emerging CNCF standard; credible signal |
| Dashboard | Live per-session score timeline, normal-vs-injected distribution plot, flagged-run cards | Uses your Matplotlib/Plotly/Streamlit-style viz strength; makes the demo visceral |

---

## 4. Innovations (lifts it above "did the assignment")

1. **Multi-signal fused anomaly score** (not a single distance metric): sequence
   surprise + frequency divergence + parameter outlier + novel-tool flag — with an
   ablation table in the PDF showing each signal's contribution. This is your
   deepfake-project "hybrid handcrafted + learned features" instinct applied here.
2. **Rigorous calibration section** with an ROC-style analysis and an explicit
   false-positive budget — the exact rigor your resume already demonstrates. Most
   candidates will ship a binary threshold; you ship a *calibrated detector*.
3. **Detection-to-governance bridge:** score crossing threshold doesn't just alert — it
   **suspends the session** (satisfies the Unit-3/Unit-4 governance spirit and the PS
   bonus in one move).
4. **Suspicion accumulator** (the PS bonus): slow-burn injections that never spike but
   persistently deviate get caught by an accumulating score with decay.
5. **Distribution-shift / drift note:** because you've *lived* the F1 0.999→0.387
   cross-domain collapse, you add a short "what happens when the agent's normal behavior
   legitimately changes (model update, new prompt)?" section with an auto-rebaseline
   trigger — a maturity signal almost no candidate will include.
6. **Reproducible evaluation harness:** the 50 normal + 3 injected scenarios are
   scripted and versioned; anyone can re-run and reproduce your numbers — the same
   evaluation discipline as your clinical-LLM benchmark.

---

## 5. Coverage map — every requested concept

| Concept | Where it appears |
|---|---|
| Agentic AI / looping | Claude Agent SDK agent with full agent loop, running multi-step tasks |
| Memory | Baseline fingerprint + per-session accumulator = cross-turn/session memory in DynamoDB; PDF paragraph on Anthropic memory-tool/context-editing influence |
| MCP | Agent consumes MCP tools; injection is delivered via MCP tool outputs |
| API & API usage | FastAPI detection service, auto-generated OpenAPI, queryable score/audit endpoints |
| RAG | **Native fit, not bolted on:** one injection scenario poisons a *retrieved document* in a small RAG tool — the canonical indirect-injection vector. Optionally use embeddings to measure semantic drift of tool outputs |
| Monitoring | OTel-GenAI-shaped logs, CloudWatch, `/health`, `/metrics`, live score dashboard |
| Error handling | Timeouts + retries/backoff on Anthropic calls, graceful degradation if scorer errors (fail-open with alert), idempotent event ingestion |
| Cloud / AWS | Lambda, API Gateway, DynamoDB, CloudWatch, SAM IaC — always-free tier (~$0/mo) |
| ML/DS in production | **The core of the project:** baseline modeling, multi-signal anomaly scoring, calibration, drift, ablation, reproducible eval harness |
| Claude Code skills | Project `CLAUDE.md` + slash commands: `/inject-sim` (run injection scenarios), `/rebaseline`, `/deploy` — described in PDF "how we built it" |
| CI/CD | GitHub Actions (private repo): unit tests + eval-harness smoke run + deploy gate |

---

## 6. Addressing Aivar's motto — customer needs in every decision

- **Persona 1 — Security/ML engineer:** needs a detector that doesn't drown them in
  false alarms → hence the calibrated threshold and documented FPR budget (a detector
  that cries wolf gets turned off — protecting the customer means precision).
- **Persona 2 — Compliance officer:** needs evidence an injection was caught and acted
  on → hence the audit log + session-suspension record.
- **Detection within one turn** is a customer-safety commitment: the faster the catch,
  the less damage a hijacked agent does to the customer's systems.
- **Explainable flags:** every alert says *which* behavioral signal fired and by how
  much — the customer's team can trust and act on it, not just see a red light.
- PDF closes with a **"Voice of the customer" table:** requirement → design decision →
  demo evidence.

---

## 7. Winning over senior ex-AWS reviewers

1. **Narrative:** "Text-based guardrails can't see a successful injection — the attack
   looks like legitimate data until the agent acts on it. So watch the *action*, not the
   *text*." Then the personal IoT-IDS bridge.
2. **Well-Architected mapping** (security, reliability, cost, operational excellence).
3. **DS rigor as the differentiator:** ROC/calibration curves, ablation, drift analysis,
   reproducible harness — this is where you out-engineer pure app builders.
4. **Comparison-to-market:** vs text classifiers (Lakera Guard, Llama Guard, OpenAI
   Moderation — they inspect prompts/outputs, not behavior), vs runtime step-level
   monitors (Zenity), vs Bedrock Guardrails (content, not behavioral-sequence). Your
   niche: *post-injection behavioral detection*.
5. **Honest limitations:** baseline needs enough normal data; sophisticated attacks that
   mimic normal tool sequences evade sequence models; single-region; OTel GenAI
   conventions still in Development status.

---

## 8. Cost plan (identical to Option A)

| Item | Cost |
|---|---|
| Lambda / API Gateway / DynamoDB / CloudWatch (free tier) | $0 |
| Anthropic API (Haiku 4.5 for ~53 scenario runs + demo) | one-time ~$3–5 credit |
| Claude Code + ChatGPT Plus (development) | existing subscriptions |
| **Total recurring** | **≈ $0/month** |

---

## 9. Deliverables plan

1. **PDF (~12–15 pages):** problem & market context (OWASP LLM01, EU AI Act Aug-2026) →
   personas → architecture diagrams (system context, event-flow sequence, scorer
   pipeline, DynamoDB model, deployment) → **DS methodology: baseline, scoring,
   calibration, ablation, drift** → design decisions with customer-impact → Well-
   Architected mapping → market comparison → limitations & roadmap.
2. **Video (5–8 min):** demo FIRST — run a normal task (low score), then the poisoned
   tool output hijacks the agent → score spikes → flagged within one turn → session
   suspended, all live on the dashboard; then the calibration plot; then architecture.
3. **Repo (zipped, never public):** README 5-min quickstart, `sam deploy` script, the
   versioned 50+3 scenario harness, seeded baseline, `.env.example`, unit tests +
   **integration tests named after each success criterion**, private GitHub Actions CI.

---

## 10. Build sequence (~5–7 days)

| Phase | Scope | Exit criterion |
|---|---|---|
| 1 | Instrumented Claude Agent SDK agent + mock MCP tools + event emission | Agent runs a task, emits clean behavioral events |
| 2 | 50 normal scenarios + baseline profiler/fingerprint | Baseline established (criterion 1) |
| 3 | Anomaly scorer + 3 injection scenarios + calibration | Criteria 2–4 pass locally, calibration plot produced |
| 4 | DynamoDB state + Lambda/SAM deploy | Criteria pass **in the deployed environment** |
| 5 | Enforcement hook + suspicion accumulator + dashboard | Criterion 5 / bonus pass deployed |
| 6 | Ablation, drift analysis, docs, diagrams, video | Submission zip complete |

---

## 11. Sources

Shares the research base in `PROJECT_PLAN.md` §11 (MCP, guardrails, AWS, Anthropic,
observability). Add for this option:
- OWASP Top 10 for LLM Applications — LLM01 Prompt Injection (indirect injection is the
  named hardest case): https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- Anthropic — building safe agents / indirect prompt injection guidance (see Agent SDK
  and agent-safety posts referenced in the main plan's source list).
