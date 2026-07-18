# Norm — The Agent Behavioral Baseline Builder
## Aivar Task · Full Project Plan (Option: PS-4.1, Unit 4 — Observability & Monitoring)
*Drafted 2026-07-13 · framed as ML-observability (not security) · deepest match to your IoT-IDS work*

> Shared production apparatus, AWS stack, cost, deliverable spec = PROJECT_PLAN.md §;
> deltas only here. Compare with the other PROJECT_PLAN_*.md + MARKET_AND_PS_RECONSIDERATION.

---

## 1. The Decision
**Build PS-4.1: an Agent Behavioral Baseline Builder** — at deployment time, auto-generate
synthetic traffic to establish an agent's *normal* behavioral fingerprint, then monitor
production against it and detect **drift**. Framed as **ML observability / MLOps**, not
security. Deployed on AWS, around a real Claude/Bedrock agent.

### Why this fits YOU
- **DEEPEST match to your resume:** this is your IoT-IDS project (behavioral baselines,
  distribution comparison, drift, F1 0.999→0.387→0.722) reframed from network traffic to
  agent behavior — but as **monitoring**, not attack detection.
- Statistics you already use: distributions, PSI/KL divergence, thresholds, calibration.

### Why it's important to AWS + Aivar
- AWS Well-Architected Agentic Lens: end-to-end observability of agent behavior. **This is
  literally Aivar's Kubogent (ML Ops) accelerator applied to agents.**
- "You can't detect abnormal behavior without knowing normal" — and new agents run
  *unmonitored* for weeks. Establishing a baseline *before* real traffic is the fix.

### Honest caveat (why it's ranked 3rd for you)
- **Most crowded market:** Arize, Fiddler, MLflow, Datadog LLM, Zenity all do agent/LLM
  drift monitoring. Differentiation must come from execution + one specific angle.
- "Anomaly detection" still sits *adjacent* to the security framing you're lukewarm on —
  though you can keep it firmly in the MLOps/monitoring lane.
- **Your differentiating angle:** **deploy-time synthetic-baseline generation** (most
  tools baseline from *production* traffic — you baseline *before* any real traffic, from
  auto-generated scenarios) + **per-intent-cluster baselines** (bonus). That "day-zero
  baseline" is the honest, defensible edge.

---

## 2. Requirements & success criteria (each → a named test + demo scene)
Build: (a) synthetic scenario generator — from an agent's system prompt + tool list,
generate 50 diverse scenarios; (b) baseline recorder — run all 50, record fingerprint
(tool-call frequency distribution, avg response length, typical tool sequences, data-access
patterns); (c) production monitor — running stats vs baseline, flag deviation beyond a
configurable threshold; (d) drift detector — auto-suggest a baseline refresh on consistent
shift.
Success: 1) baseline established from synthetic scenarios *before* real traffic; 2) three
production scenarios → normal (no flag) / moderate (warning) / severe (alert); 3) drift
detected on a simulated model update that changes tool-call patterns.
Bonus: **cluster scenarios by intent** (retrieval / modification / communication) → keep
per-cluster baselines for finer monitoring.

---

## 3. Architecture
```
 Agent system prompt + tool list
            │
            ▼
 ┌────────────────────┐   50 synthetic scenarios   ┌──────────────────────┐
 │ Scenario generator  │ ─────────────────────────► │ Agent (Claude/Bedrock)│
 │ (LLM-driven)        │                            │ runs each scenario    │
 └────────────────────┘                             └──────────┬───────────┘
                                                     behavioral events
            ┌────────────────────────────────────────────────┘
            ▼
 ┌───────────────────────────────────────────────────────────────┐
 │  NORM service (FastAPI on AWS Lambda)                            │
 │  ┌──────────────┐   ┌────────────────────────────────────────┐ │
 │  │ Baseline      │   │ Production monitor: running stats vs    │ │
 │  │ recorder →    │──►│ baseline → normal / warning / alert     │ │
 │  │ fingerprint   │   │ (PSI / KL divergence, thresholds)       │ │
 │  │ (distributions│   └───────────────────┬────────────────────┘ │
 │  │  + sequences) │   ┌───────────────────▼────────────────────┐ │
 │  └──────────────┘   │ Drift detector → suggest baseline refresh│ │
 │  (per-intent cluster baselines, bonus)  └─────────────────────┘ │
 └───────────────────────────┬─────────────────────────────────────┘
                             ▼
                 DynamoDB (baselines, running stats, alerts) · S3 (scenario sets)
                 CloudWatch / OTel · Dashboard: baseline vs live distributions,
                 drift timeline, per-cluster monitors
```

## 4. Component decisions (deltas)
- **Fingerprint = multi-distribution:** tool-call frequency, sequence n-grams, response-
  length distribution, data-access patterns. Compared with **PSI / KL / JS divergence** —
  standard drift statistics you can name and defend (PSI>0.1 = drift is an industry norm).
- **Synthetic generation:** LLM produces diverse scenarios spanning the tool space; you
  document coverage/diversity (a small DS analysis).
- **Calibration of thresholds** (normal/warning/alert) = your calibration skill; document
  the false-alarm tradeoff.
- Rest = shared apparatus (Lambda, DynamoDB, S3, API Gateway, CloudWatch, SAM, CI/CD, OTel).

## 5. Innovations
1. **Day-zero baseline from synthetic traffic** (vs production-only baselining) — the angle.
2. **Multi-distribution fingerprint + standard drift stats (PSI/KL)** with documented
   calibration — your DS rigor.
3. **Per-intent-cluster baselines** (bonus) — finer-grained "normal" per task type.
4. **Drift→refresh suggestion loop** — closes the MLOps monitoring loop (Kubogent-flavored).

## 6. Coverage map
Agentic AI (agent under observation) · MCP (its tools) · **DS core** (baselines, drift,
PSI/KL, calibration, synthetic-data generation) · LLM (scenario generation) · memory
(stored baselines) · monitoring/OTel (the whole point) · error handling · **AWS + DevOps**
(deploy + IaC + CI/CD). RAG optional.

## 7–11. Motto · Reviewers · Cost · Deliverables · Build (tailored)
- **Customer:** the customer's agent is monitored from *day one*, not after weeks
  ungoverned — earlier detection = less harm. Persona: ML/platform engineer.
- **Reviewers:** Well-Architected observability mapping; named drift statistics;
  calibration/false-alarm analysis; **honest market comparison (this is the crowded one —
  lead with the day-zero-synthetic-baseline differentiator)**; scope limits.
- **Cost:** ~$0/mo free tier + ~$5 Bedrock/Anthropic (50 scenario runs + demo).
- **Deliverables:** PDF + required diagrams; video (demo first: baseline built pre-traffic,
  then normal/warning/alert scenarios live, then drift on a simulated model swap); repo +
  README + one-command deploy.
- **Build (Wed-night→Sat):** P1 scenario generator + agent runner → P2 baseline recorder +
  fingerprint → P3 production monitor + drift detector → P4 AWS deploy (SAM) → P5 dashboard
  + per-cluster baselines → P6 calibration/coverage analysis, docs, video.

## 12. Sources / differentiation
AWS Agentic AI Lens (observability); market: Arize, Fiddler, MLflow, Datadog LLM, Zenity,
ARMO (baseline/drift). PSI>0.1 drift norm. Links in MARKET_AND_PS_RECONSIDERATION.md.
NOTE: most crowded market of the three — differentiate on day-zero synthetic baselining.
