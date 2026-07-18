# PROJECT PLAN — PS-4.3 Cross-Session Adversarial Pattern Detector ("Vigil")

*Build spec, Jul 16 2026. Window: Thu night → Sat night. Decision rationale in
`MARKET_RESEARCH_FINAL_PS_DECISION_2026-07-16.md`. Fallback PS if Thu goes badly: PS-5.3.*

## One-line pitch
Per-request guardrails judge messages in isolation. A patient attacker never loses in a
single message — they probe across MANY sessions, each one individually benign, gradually
mapping the policy boundary. **Vigil is the SOC layer above the guardrail**: it correlates
guardrail outcomes and request patterns per user identity across sessions, accumulates a
decaying risk score, and raises one explainable alert card when a probing / escalation /
enumeration campaign emerges. Nothing on the market does this for LLM apps (2026: research
papers only — FragBench, cross-session threat benchmarks).

## What we must prove (success criteria, verbatim mapping)
1. Boundary-probing user: 20 sessions of gradually varied blocked prompts → flagged. ✅ Detector A
2. Data-scraping user: 50 sessions of sequential entity enumeration → flagged. ✅ Detector C
3. Benign high-volume user (many sessions, diverse legit queries) → NO alert. ✅ calibration
4. Risk accumulates across sessions and resets after a configurable inactivity window. ✅ risk engine
5. Bonus: pattern clustering by technique + threat summary card per flagged user. ✅ alert card

## System architecture (all AWS, serverless, ~free-tier)

```
 attacker/benign sims ──► DEMO SUPPORT AGENT (the governed workload)
                          FastAPI on Lambda + Bedrock Claude Haiku
                          + Bedrock Guardrails (or lightweight policy check)
                               │  emits SessionEvent per turn (middleware)
                               ▼
                     VIGIL INGEST API  (API GW → Lambda, FastAPI/Mangum)
                          │ validate, idempotency-key, store
                          ▼
                     DynamoDB: events (PK user_id, SK ts) · user_risk · alerts
                          │
                     DETECTION PIPELINE (same Lambda, sync per event; SQS noted
                          │              as the scale path in the write-up)
                          ├─ A. Boundary-probing: embeddings of BLOCKED prompts
                          │    (Bedrock Titan Embeddings v2) → cosine cohesion of a
                          │    user's block history + block-rate trajectory
                          ├─ B. Escalation: map each request to a capability tier
                          │    (rules + embedding similarity to tier prototypes);
                          │    monotone tier climb across sessions + denials
                          ├─ C. Enumeration: entity-masked template mining →
                          │    same-template count with structured slot variation
                          │    (sequential IDs, low-entropy diffs)
                          ▼
                     RISK ENGINE: evidence-weighted score, exponential decay
                     (half-life h), hard reset after inactivity window W;
                     threshold θ calibrated on simulated cohort (target FPR ≈ 0
                     on benign heavy user)
                          ▼
                     ALERT: SNS/webhook + LLM-written (Haiku) threat summary card
                     {user, technique cluster, evidence, sessions involved, score curve}
                          ▼
                     DASHBOARD: static S3 page polling /users /alerts /risk APIs
```

## Tech stack (locked)
- **Python 3.12, FastAPI + Mangum on Lambda**, API Gateway (HTTP API), health check `/healthz`.
- **DynamoDB** (on-demand): `events`, `user_risk`, `alerts` — TTL on events = retention policy.
- **Bedrock**: Claude Haiku (demo agent + alert summaries), Titan Text Embeddings v2
  (probing detector). Region: us-east-1.
- **numpy + rapidfuzz** (cosine, template similarity). No model training. No heavy deps.
- **IaC: AWS SAM** (one `template.yaml`, one-command deploy — "automated deployment
  scripts" submission requirement). **CI/CD: GitHub Actions in a PRIVATE repo**
  (Aivar rule: never public) — lint, tests, sam validate, deploy on main.
- **Observability**: structured JSON logs (CloudWatch), one CloudWatch alarm (errors),
  request IDs end-to-end.
- Dashboard: single static HTML+JS (fetch polling) on S3. No framework.

## Production-thinking ledger (the differentiator — goes in write-up + DECISIONS.md)
- **Token cost**: embed ONLY blocked/flagged prompts (a tiny fraction of traffic), cache
  by prompt hash; LLM summary generated only ON ALERT. Detection itself is $0-per-event
  math. Cost table in write-up: per 100k events ≈ a few cents.
- **Call volume / concurrency**: idempotency keys on ingest, DynamoDB on-demand,
  conditional-write race safety on risk updates; sync pipeline now, SQS decoupling
  documented as the scale path (decision recorded, not hand-waved).
- **Decay computed lazily** at read/update time from (last_score, last_ts) — no cron, no
  idle compute. Classic serverless decision; explain it in the video.
- **Retention/PII**: events carry prompt hashes + embeddings, raw text only for blocked
  prompts, TTL-expired; user IDs pseudonymous.
- **Failure modes**: Bedrock throttle → exponential backoff, detector degradation (A can
  fall back to lexical similarity if embeddings unavailable); ingest NEVER blocks the
  demo agent (fire-and-forget middleware with timeout).
- **Calibration honesty**: publish the score distributions (benign vs each archetype),
  chosen θ, and the borderline cases — evaluators trust measured numbers over adjectives.

## The DS core (what Sri defends in the interview — her IoT-IDS story transplanted)
1. **Detector A (probing)** = semantic cohesion of a user's blocked-prompt history: high
   mutual cosine similarity among blocks = paraphrase probing, diverse blocks = ordinary
   clumsiness. Plus trajectory: block-rate over sessions.
2. **Detector B (escalation)** = capability ladder (read → summarize → modify → export →
   admin); requests mapped by prototype similarity; a user whose *max requested tier*
   climbs monotonically across sessions while being denied = escalation probing.
3. **Detector C (enumeration)** = mask entities → template hash; one template repeated
   with structured slot variation (sequential integers, alphabetical walks, low-entropy
   diffs) = scraping. Kendall-tau / diff-entropy on slots.
4. **Risk engine** = weighted evidence with exponential decay + inactivity reset — same
   math as intrusion-detection risk accumulation; threshold from simulated-cohort ROC.

## Build workflow (night-by-night, Claude ↔ Codex split per CLAUDE_CODEX_WORKFLOW.md)
- **Thu night (tonight)**: lock PS ✋(Sri confirms) → scaffold repo (private) → SAM
  skeleton + DynamoDB tables + ingest API + demo support agent w/ middleware → deploy
  walking skeleton to AWS (end-to-end event flowing). *Codex: scaffold, SAM, CI. Claude:
  event schema, API contracts, review.* Milestone: one simulated turn lands in DynamoDB
  via the deployed stack.
- **Fri night** (Claude weekly budget resets Fri 9:29am — heaviest Claude day): detectors
  A/B/C + risk engine + simulator (3 archetypes + benign heavy user) + calibration run;
  record distributions. *Claude: detector logic + calibration. Codex: simulator, tests,
  dashboard shell.* Milestone: all 4 success-criteria scenarios pass against the DEPLOYED
  stack.
- **Sat**: alert cards + dashboard polish + hardening (error paths, health, alarm) →
  README + architecture diagram + PDF write-up (market comparison from the research doc,
  citing AgentCore/Zenity/Lasso as per-request vs Vigil cross-session) → record 5–8 min
  video (DEMO FIRST: run the probing sim live, watch risk climb, alert fire) → zip →
  submit Saturday night. TCS NQT Sunday 8am untouched.
- Throughout: EXPLAINER.md / EXPLAINER_workbook.md / DECISIONS.md updated at each
  milestone (Claude drafts; Sri rewrites in her own words same night).

## Submission checklist (from Aivar rules)
zip = code + README + one-command deploy scripts + PDF write-up (problem, solution,
architecture diagrams, market comparison) + 5–8 min video (demo first). Private repo only.
Confirm the exact Sunday deadline time — plan assumes Sat-night submission regardless.

## v2 upgrades (Jul 16 evening — adopted from cross-review of Codex's ProofLoop/AegisFlow dossiers)
1. **Aivar framing (verified from aivar.tech):** pitch Vigil as a Day-2 governance layer —
   "Let's solve the Day 2 problem of AI, led by Governance & Integration." Alert cards =
   "No Black Boxes" evidence: every flag shows per-detector contributions, the sessions
   involved, and the score curve — you always know WHY a user was flagged. Customer is the
   fifth element → the demo workload is a Velogent-style customer-facing support/invoice
   agent, i.e., the kind of system Aivar actually deploys.
2. **Honest market comparison (softened, stronger):** nearest neighbors are Lakera Agent
   Behavior Defense (per-AGENT behavioral intent, single-workflow) and classic fraud/abuse
   platforms (per-user scoring, non-LLM signals). Neither correlates per-USER behaviour
   across sessions of an LLM app. Never claim "first/only/no competitor."
3. **Claims discipline (from Codex, adopted wholesale):** never claim exactly-once
   (idempotent handlers + conditional writes = exactly-once EFFECT), never claim
   detects-all-attacks, report FPR/recall only on the versioned simulated cohort.
4. **Monitor the monitor:** `/healthz` exposes ingest lag, last-event timestamps per
   source, embedding-call error rate, and DLQ depth — so a silent Vigil failure can never
   masquerade as "no attacks detected." A stale event stream is itself an alert.
5. **Cost hygiene:** AWS Budget alarm from the first deploy + a `sam delete` teardown
   script; GitHub-OIDC in CI (no long-lived AWS keys); report actual bill-to-date in the
   write-up rather than claiming "free."
6. **Demo-first video:** outcome in the first 90s — run the probing sim live, watch the
   per-user risk climb across sessions, the alert card fire, and the benign heavy user stay
   quiet — then architecture and design trade-offs.

## Business case for the write-up intro (from the Databricks/Drive research)
Lead with the post-deployment governance gap, now backed by numbers (see
`DATABRICKS_INTEL_FOR_WRITEUP.md`): ~60% of firms govern AI before deployment but **fewer
than 40% keep governing after go-live** — the exact window cross-session probing exploits;
"real-time monitoring → a third fewer failures"; governance using-tools → 12× more projects
to production. Vigil is the runtime, cross-session layer that gap is missing.

## Research status
- [x] Databricks/Drive guides mined end-to-end → `DATABRICKS_INTEL_FOR_WRITEUP.md`.
- [x] Cross-evaluation vs Codex complete → verdict holds (PS-4.3 Vigil).
- [x] Market/whitespace research complete → `MARKET_RESEARCH_FINAL_PS_DECISION_2026-07-16.md`.

## Open items (user dependencies only — NOT open research; the `[ ]` are to-dos, not truncation)
- [ ] Sri confirms PS-4.3 (else fallback PS-5.3 — contained, spec sketch in research doc)
- [ ] AWS account ready + Bedrock model access enabled (Haiku + Titan Embeddings, us-east-1)
- [ ] Exact Aivar deadline time (plan assumes Sat-night submission regardless)

--- END OF PLAN ---
