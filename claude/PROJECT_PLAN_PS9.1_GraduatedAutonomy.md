# Gradient — The Graduated Autonomy Engine
## Aivar Task · Full Project Plan (Option: PS-9.1, Unit 9 — Human-in-the-Loop & Oversight)
*Drafted 2026-07-13 · non-cybersecurity · most central non-security governance primitive*

> Shared production apparatus, AWS stack, cost, deliverable spec = PROJECT_PLAN.md §;
> deltas only here. Compare with the other PROJECT_PLAN_*.md + MARKET_AND_PS_RECONSIDERATION.

---

## 1. The Decision
**Build PS-9.1: a Graduated Autonomy Engine** — score every agent action on risk, then
route it to the right oversight level: **autonomous** (low), **confirm** (medium), or
**human review** (high). With a self-calibrating threshold that learns from user
confirm/reject behavior. Deployed on AWS, governing a real Claude/Bedrock agent.

### Why this fits YOU
- **Risk scoring + calibration = your deepfake-detector work** (Optuna tuning + logistic-
  regression calibration + stratified CV). The adaptive-threshold bonus is rich DS.
- **Confidence estimation** (one of the 4 risk dimensions) is model-uncertainty work — DS,
  not security.
- **Zero cybersecurity.** The frame is *oversight and efficiency*, not attacks.

### Why it's important to AWS + Aivar
- **HITL is an EU AI Act Art. 14 legal requirement AND an AWS Well-Architected Agentic-Lens
  principle** ("proportionate human oversight"). Singapore's graduated-autonomy framework
  is the emerging global model.
- The core tension — *full autonomy is risky, full gating kills the value* — is THE
  practical blocker to enterprise agent adoption. Solving it well is high-impact.
- Aivar's Velogent (agentic automation) needs exactly this to be safely deployable.

### Differentiation (honest, defensible)
Most HITL today is **binary** (OpenAI Agents SDK pause/approve; Galileo; Strata) — a human
approves or the agent runs free. Your edge: **dynamic, multi-dimension risk scoring +
self-calibrating thresholds** so oversight is *proportional and adaptive*, not on/off.
That's newer and less commoditized. Be clear what you DON'T do (not a full workflow engine).

---

## 2. Requirements & success criteria (each → a named test + demo scene)
Build: (a) risk scorer over 4 dimensions — **reversibility, data scope, regulatory
category, LLM confidence**; (b) risk→autonomy mapping (low→auto, medium→preview+confirm,
high→review queue); (c) confirmation interface (CLI/webhook sim ok); (d) audit record with
the full risk-score breakdown.
Success: 1) bulk DB delete (high) → full review; 2) single-record update (medium) → user
confirmation; 3) read-only query (low) → autonomous; 4) risk breakdown accurate +
human-readable in the audit log.
Bonus: **adaptive threshold calibration** — if users consistently confirm an action type
unchanged, lower its risk over time; if they modify/reject, raise it.

---

## 3. Architecture
```
 Agent (Claude/Bedrock) proposes action ─────────────────┐
                                                          ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  GRADIENT engine (FastAPI on AWS Lambda)                        │
        │  ┌───────────────── Risk Scorer ─────────────────┐             │
        │  │ reversibility · data-scope size · regulatory   │  score      │
        │  │ category · LLM confidence  → weighted risk 0-1 │────┐        │
        │  └────────────────────────────────────────────────┘    ▼        │
        │                         ┌──────── Risk→Autonomy router ───────┐ │
        │                         │ low → AUTONOMOUS (execute)          │ │
        │                         │ med → PREVIEW + CONFIRM (user)      │ │
        │                         │ high → HUMAN REVIEW QUEUE           │ │
        │                         └───────┬───────────────┬────────────┘ │
        │  ┌──────────────────────────────┘               ▼              │
        │  │ Adaptive calibrator (learns thresholds   Review queue        │
        │  │ from confirm/reject history)             (DynamoDB)          │
        │  └──────────────────────────────┐               │              │
        └─────────────────┬───────────────┘───────────────┘              │
                          ▼                                               │
                 DynamoDB (actions, scores, thresholds, queue, audit) ◄───┘
                 CloudWatch / OTel traces · Dashboard: risk distribution,
                 routing outcomes, per-action-type calibration curves
```

## 4. Component decisions (deltas)
- **Risk scorer:** transparent weighted function over 4 features → 0–1 score, mapped to
  bands. Every score is **explainable** (per-dimension contribution in the audit log) —
  seniors love glass-box scoring for governance.
- **Confidence dimension:** derive LLM confidence (e.g., self-reported + response
  consistency across samples) — a real DS sub-problem you can discuss.
- **Adaptive calibration = the DS centerpiece:** model threshold updates as an online
  process; document the update rule, guardrails against runaway drift, and a
  precision/over-blocking tradeoff analysis. This is your calibration expertise.
- Rest = shared apparatus (Lambda, DynamoDB, S3, API Gateway, CloudWatch, SAM, CI/CD, OTel).

## 5. Innovations
1. **Proportional, multi-dimension risk scoring** vs binary HITL — the market gap.
2. **Self-calibrating thresholds** that learn from human decisions (bonus) — your DS edge,
   with a documented drift-guard + over-blocking analysis.
3. **Glass-box, per-dimension explainable scores** in every audit record.
4. **Reviewer-agreement analytics** (extend the bonus): flag action types where humans
   systematically override the engine → policy-recalibration signal.

## 6. Coverage map
Agentic AI (agent proposing typed actions) · MCP (the tools it acts through) · HITL
(the whole point; AWS + EU AI Act) · **DS core** (risk scoring + adaptive calibration +
confidence estimation) · LLM (confidence, action generation) · memory (per-action-type
threshold state) · monitoring/OTel · error handling · **AWS + DevOps** (deploy + IaC +
CI/CD). RAG optional (a lightweight regulatory-category lookup could use retrieval).

## 7–11. Motto · Reviewers · Cost · Deliverables · Build (tailored)
- **Customer:** oversight without bottleneck — the customer keeps control on high-stakes
  actions AND keeps automation value on trivial ones. Both personas: platform engineer +
  compliance officer.
- **Reviewers:** Well-Architected HITL mapping; glass-box scores; calibration/over-blocking
  analysis; market comparison (binary HITL vs proportional+adaptive); honest scope limits.
- **Cost:** ~$0/mo free tier + ~$3–5 Bedrock/Anthropic credit.
- **Deliverables:** PDF + required diagrams (incl. a HITL state machine + risk-to-autonomy
  flow); video (demo first: read→auto, update→confirm, bulk-delete→review, then the
  calibration curve moving as users confirm/reject); repo + README + one-command deploy.
- **Build (Wed-night→Sat):** P1 risk scorer + tests → P2 router + confirmation interface →
  P3 review queue + audit (DynamoDB) → P4 AWS deploy (SAM) → P5 adaptive calibrator +
  dashboard → P6 calibration/over-blocking analysis, docs, video.

## 12. Sources / differentiation
EU AI Act Art. 14; AWS Well-Architected Agentic AI Lens (proportionate oversight);
Singapore graduated-autonomy framework; market: OpenAI Agents SDK HITL, Galileo, Strata
(binary approve/pause). Links in MARKET_AND_PS_RECONSIDERATION.md.
