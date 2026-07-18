# ProofLoop — Build Workflow, Tech Stack, and Claude-Code+Codex Playbook
*Jul 17 2026. Answers: (1) can we extend Phase-1 to the broad scope later? (2) Claude Code
vs Codex — strengths/weaknesses/models/use-cases for OUR build. (3) the workflow + stack.
Includes a critical review of Codex's proposal — which is mostly right, with one real flaw.*

## 0. TL;DR verdict on Codex's proposal
Codex's **strategy is correct**: build an *extension-ready vertical slice*, not a throwaway
demo and not the full platform. Its **interface discipline is excellent** and I adopt it
wholesale. **But its Phase-1 tech stack is still too heavy for you** (zero AWS background,
~2.5 nights): it quietly re-introduces Strands + AgentCore Gateway + Cognito + React + CDK
+ X-Ray. That's scope-creep wearing an "extension-ready" label. You get the SAME
extensibility from clean *interfaces* on a *simple* stack. My stack below strips Phase-1 to
what one person can actually deploy this week, while keeping every seam Codex identified so
Phase-2 bolts on without a rewrite.

---

## 1. "Can we extend this to the broad scope if we finish soon?" — YES, with two caveats
**Yes** — if Phase-1 is built on the stable contracts below, the broad ProofLoop bolts on
without rewriting the core. That's real and worth designing in (it costs almost nothing).

**Caveat 1 — do NOT attempt to extend before submission.** Extension is Phase-2, for the
interview-wait window (after Saturday). Trying to grow the scope before the deadline is how
the submission dies. Ship Phase-1 complete; *present* Phase-2+ as a roadmap.

**Caveat 2 — extension-readiness is mostly an INTERFACE property, not an infrastructure
one.** You do not need AgentCore/Strands/Cognito in Phase-1 to be extension-ready. You need:
- **Adapter seams** (from commit 1): `ModelProvider`, `WorkloadRuntime`, `EvidenceSource`,
  `ControlEvaluator`, `CanaryRunner`, `StatusRepository`, `IncidentSink`. Phase-2 swaps a
  plain-Lambda `WorkloadRuntime` for an AgentCore one behind the same interface — no core change.
- **Versioned evidence schema** (Codex's field list is good — keep it verbatim), **`tenant_id`
  from day 1**, **append-only evidence**, **status separate from transition history**,
  **compliance state outside the LLM**, **MCP tool contracts from the start**.
Adopt all of these. They're the genuinely valuable part of Codex's doc.

---

## 2. The stack — my simplified Phase-1 vs Codex's (build the left column)
| Layer | **Phase-1 (BUILD THIS — finishable)** | Codex's Phase-1 (too heavy) | Phase-2 swap-in |
|---|---|---|---|
| Language | Python 3.12 | Python + TypeScript | + TS |
| Agents | **Plain Python 2-agent orchestration** (extraction → reconciliation), typed tools | Strands Agents + Graph | Strands / AgentCore Runtime |
| Model | **Bedrock `InvokeModel`, Claude Haiku 4.5**, behind a `ModelProvider` adapter | Haiku via Strands/Bedrock | Sonnet if eval justifies |
| Tool layer | **Lightweight Python MCP server** (keeps the MCP trend, no managed service) | AgentCore Gateway (MCP) | AgentCore Gateway + Cedar |
| Compute | **AWS Lambda (zip) + API Gateway HTTP API**, FastAPI+Mangum | Lambda container | AgentCore Runtime |
| State | **DynamoDB** (tenant-scoped keys, TTL, conditional writes) | DynamoDB | + S3 evidence archive |
| Schedule | **EventBridge Scheduler** (5-min reconciliation) | EventBridge | + webhooks |
| Reliability | **SQS + DLQ + idempotency keys** on ingest only | SQS/DLQ everywhere | split queues |
| Guardrail | **Bedrock Guardrails** (one, real) | Bedrock Guardrails | per-control policies |
| Observability | **Structured JSON logs + CloudWatch; `/healthz`** | OTel/ADOT + X-Ray | AgentCore Observability |
| Auth | **API key / simple JWT** (demo roles) | Cognito | Cognito + SSO |
| Dashboard | **Static HTML + vanilla JS** (fetch-poll) on S3 | React/Vite | React evidence explorer |
| IaC | **AWS SAM** (one `template.yaml`, one-command deploy) | AWS CDK | CDK modular stacks |
| CI/CD | **GitHub Actions + AWS OIDC** (private repo) | same | + staging/prod gates |
| Tests | **pytest + Hypothesis (state machine) + moto** | + Playwright/Locust | + chaos/replay |
| Clock | **Injectable virtual clock** for 24/48h demo | same | real timers |

**Why simpler wins here:** every managed service you drop (AgentCore Gateway, Cognito,
Strands, React, CDK, X-Ray) is a learning cliff for someone new to AWS, and each is a place
the deploy can stall on night one. SAM over CDK only because it's the shortest path to
"deployed" for a first-timer (Codex prefers CDK for the AgentCore constructs — valid for
Phase-2; overkill now). **Everything cut is a clean Phase-2 swap, not a rewrite** — that's
the whole point of the adapters.

**Two deliberate "trend" inclusions kept in Phase-1** (so it reads current to ex-AWS eyes):
real **multi-agent** workflow (2 agents, distinct authority) and **MCP** tool contracts.
Both are cheap on the simple stack and both matter to Aivar/the rubric.

---

## 3. Claude Code vs Codex — the honest 2026 picture (fresh research, tied to our build)
*Both are worth using; you pay for both (Claude Code sub + ChatGPT Plus/Codex). Neither
subscription funds the deployed Bedrock model — AWS bills that separately.*

### Strengths / weaknesses (verified Jul 2026)
| | **Claude Code** | **OpenAI Codex** |
|---|---|---|
| Code quality | Wins blind reviews **67%** vs 25%; thorough, better error handling | Leaner code |
| Long context / sessions | **Better** (1M ctx, long-session memory) — good for architecture | 272K default (opt-in ~1M) |
| Terminal / DevOps / autonomy | Strong | **Best** (Terminal-Bench lead; ran 7h+ unattended) |
| Token efficiency | ~4× heavier | **~4× leaner** → offload bulk gen here to save your Claude budget |
| Parallel model | **Agent Teams** = coordinated subagents for *dependent* subtasks | Cloud worktrees = **independent** parallel tasks (explorer/worker/default, up to ~6–8) |
| Repo isolation | Worktrees (v2.1.49) + `isolation: worktree` subagents | Each task its own cloud env + worktree |
| Review | Staff-eng architectural / invariant review | PR/diff review with evidence |
| Best-fit role here | **Architect · ML/agent logic · contracts · final quality + security review** | **IaC/CI · dashboard · test suite · terminal/deploy · independent parallel chunks** |

One-line memory (unchanged, still true): **Claude = think, architect, reason, review.
Codex = execute fast, terminal/DevOps, run parallel, save tokens.**

### Which MODEL for which task (current, verified)
Claude models — SWE-bench Verified: **Fable 5 ≈95%**, **Opus 4.8 ≈88.6%**, Sonnet 5 close
behind; **Terminal-Bench: Sonnet 5 (80.4) actually BEATS Opus 4.8 (74.6)**. Pricing/M tok:
Fable **$10/$50**, Opus **$5/$25**, Sonnet **$2/$10** (intro). Codex model: **GPT-5.3-Codex**,
effort low/medium/high/xhigh (xhigh = deep multi-step planning; 77.3% Terminal-Bench 2.0).

| Task in OUR build | Claude Code | Codex |
|---|---|---|
| Architecture, event schema, failure model, ADRs | **Opus 4.8** (`/model opusplan`) | GPT-5.3-Codex `high/xhigh` for the adversarial critique |
| Contracts, ML/agent logic, state-machine design | **Opus 4.8 → Sonnet 5** to implement | review only |
| Routine implementation (handlers, repos, endpoints) | **Sonnet 5** (default) | GPT-5.3-Codex `medium/high` |
| IaC (SAM), CI/CD, dashboard, test suite, deploy | Sonnet 5 (or hand to Codex) | **GPT-5.3-Codex `high`** (its strength) |
| Terminal/deploy runs, integration owner | Sonnet 5 | **Codex** (best autonomy) |
| Hard debugging | **Opus 4.8** high; Fable 5 only if it stalls | GPT-5.3-Codex `xhigh` |
| Mechanical edits / quick subagents | **Haiku 4.5** | mini model if available |
| Final cross-review before merge | **Opus** reviews Codex's code | Codex reviews Claude's code |

**Rules:** default to **Sonnet 5** (it even out-agents Opus on the terminal, and it's the
cheapest). Escalate to **Opus 4.8** only for architecture/hard-reasoning. Use **Fable 5**
sparingly — one genuinely hard problem at a time (it's 5× Sonnet's price). Anthropic's own
guidance: plan with Opus, execute with Sonnet, mechanical with Haiku.

### Agentic-AI use cases each tool makes simpler — mapped to ProofLoop
- **Claude Code makes simpler:** the **agent + tool logic** (the 2-agent workflow, MCP tool
  definitions, the Bedrock adapter), the **deterministic assurance engine** (careful
  invariant reasoning — "LLM never decides compliance"), the **contracts/schemas**, and the
  **write-up narrative + honest limitations**. Long-context architecture is its home turf.
- **Codex makes simpler:** the **SAM/IaC + GitHub-OIDC CI**, the **static dashboard**, the
  **test harness** (property tests for the state machine, idempotency/out-of-order/duplicate
  fixtures), and **running the deploy end-to-end** (terminal autonomy). Independent chunks
  → its cloud worktrees shine.

### Weaknesses to actively manage
- **Codex:** broad instructions → broader-than-needed builds (this is exactly why its
  Phase-1 bloated); give it *narrow, testable* tasks. Worktrees need disciplined git handoff.
- **Claude Code:** long sessions burn context + weekly budget fast on Opus/Fable → stay on
  Sonnet, `/clear` between tasks, `/compact` within a task, delegate log-heavy work to a
  Haiku subagent.
- **Both:** can hallucinate current AWS syntax; neither may self-certify production-readiness
  → cross-model review + actually run it (the `verify` discipline).

---

## 4. The build workflow (solo dev + 2 assistants — kept lean on purpose)
For a 2.5-night solo build, skip the elaborate 3-parallel-agent + skills + hooks machinery
Codex proposed — that scaffolding is itself a time sink. Lean version:

**Step 0 — one source of truth.** Private repo, baseline commit, protect `main`. One
`CLAUDE.md` + one `AGENTS.md` both pointing at `docs/PROJECT_RULES.md` (don't duplicate).

**Step 1 — architecture gate (no code yet).** Claude/Opus drafts component boundaries +
versioned evidence schema + failure model + the 7 adapter interfaces. Codex/GPT-5.3 attacks
it for over-scope + AWS pitfalls. You approve a frozen 1-page design + ADRs.

**Step 2 — contracts first.** Claude Code (Sonnet) writes evidence schema, control-status
schema, MCP tool schemas, API request/response, error taxonomy, fixtures, contract tests.
Codex reviews. Once merged, field names are locked.

**Step 3 — parallel build (clear ownership, cross-review before merge):**
- **Claude Code owns:** 2-agent workflow, MCP tools, Bedrock `ModelProvider`, guardrail
  middleware, canary runner, deterministic assurance state machine (the invariant core).
- **Codex owns:** DynamoDB repo, evidence collector, EventBridge reconciliation, API
  endpoints, SAM infra, GitHub-OIDC CI, static dashboard, state-machine + integration tests.
- Every PR: the *other* model reviews (correctness/security/cost if Claude authored;
  architecture/invariants/contracts if Codex authored). Author fixes. Then merge. **No model
  reviews only its own work.**

**Step 4 — integration & deploy (Codex is integration owner — best terminal autonomy).**
`sam build/deploy` to a dev stack → run one real invoice → confirm evidence in DynamoDB →
run the PII canary → wait one 5-min cycle → confirm dashboard/timeline → inject the virtual
clock for 24/48h transitions → confirm recovery-to-green needs fresh proof → capture real
logs + AWS cost. Claude independently reviews IAM, failure paths, and status semantics.

**Step 5 — evaluation & docs.** Codex owns the automated harness (state-transition property
tests, missing/stale/contradictory evidence, idempotency, dup/out-of-order, canary
false-pos/neg). Claude owns interpretation: what it proves, what it doesn't, honest limits,
market comparison. You rewrite the narrative in your own voice. Video: deployed outcome
first, then architecture/trade-offs; include an implemented-vs-demonstrated-vs-future table.

**Budget guardrails (both agree):** AWS Budget alarms at $5/$10; Haiku default at runtime,
LLM explanation only on status transition; 7-day CloudWatch retention; DynamoDB TTL;
`sam delete` teardown; no NAT/OpenSearch/EKS/always-on container. Target < $10 for the demo,
report actual spend (never claim "free").

---

## 4b. AWS not needed for ~24h — the LOCAL-FIRST plan (build now, deploy later)
The account takes ~24h to activate. This costs us nothing: because the core is
provider-neutral, **~80% of the project is built and tested on your laptop with zero cloud.**
Concrete order for the next 24h (all local):
1. **Repo skeleton** (private) + `CLAUDE.md` + `AGENTS.md` → both point to `docs/PROJECT_RULES.md`.
2. **Contracts first** — the 7 adapter interfaces + versioned evidence schema + control-status
   schema + MCP tool schemas + error taxonomy + fixtures + contract tests. (No cloud needed.)
3. **The 2-agent workflow** (extraction → reconciliation) running locally against **free
   Gemini** (dev model), typed MCP tools, guardrail middleware (free Presidio/regex PII).
4. **The deterministic assurance engine** (green/amber/red + UNKNOWN state machine) with an
   **in-memory / local-DynamoDB (moto or DynamoDB-Local)** `StatusRepository` — fully testable
   offline with the injectable virtual clock.
5. **Property + unit tests** for the state machine (the invariant core) — all local.
6. **Static dashboard** (HTML/JS) reading a local API.
Only AFTER activation do we bind the AWS adapters + `sam deploy`. So start tonight; AWS
catches up tomorrow. Dev runs on free Gemini → swap to Bedrock (credit-funded) for the final
demo once access is approved.

## 4c. Collaboration update (verified Jul 2026) — Codex now runs INSIDE Claude Code
- **OpenAI Codex plugin for Claude Code** (shipped 2026) lets Claude Code delegate a task to
  Codex and get it back for review — a **cross-provider review loop in one shared folder**.
  Codex writes a `handoff.md` (what it produced, decisions made, what it recommends next);
  Claude Code reads it and continues. This makes the cross-review workflow practical, not manual.
- **Why cross-model review is worth the extra cycle (evidence):** Codex and Claude share no
  training data/architecture, so they **fail differently** — the class of bug one misses, the
  other tends to catch (async races, injection vectors, invariant violations). Same-model
  self-review "grades its own homework" through the lens that made the bug. For governance
  code where a missed invariant is a real defect, **decorrelated review is the point.** Rule
  stays: the other model's finding is *input, not verdict* — verify, keep what's confirmed.
- **Instruction files:** `CLAUDE.md` (Claude Code) + `AGENTS.md` (Codex) both reference ONE
  canonical `docs/PROJECT_RULES.md` so neither drifts. Codex can auto-generate `AGENTS.md`
  from `CLAUDE.md`.

## 4d. CORRECTIONS from Codex's Jul-17 cross-review (verified — adopt these)
1. **Codex models: my GPT-5.3-Codex was DATED.** OpenAI shipped **GPT-5.6 (Sol/Terra/Luna)
   on Jul 9 2026** (verified). Tiers: **Sol** = flagship coding ($5/$30), **Terra** =
   balanced ($2.50/$15), **Luna** = cheapest ($1/$6). Notably **Sol@max = 80 on the Coding
   Agent Index, ~2.8 above Fable 5 at ~1/3 the cost** → for the HARDEST problems, prefer
   Codex-Sol over Claude-Fable. Use **Terra** for routine Codex work, **Sol high/xhigh** for
   architecture critique / hard debug / AWS integration / final review. Replaces every
   "GPT-5.3-Codex" mention below.
2. **Bedrock model = Amazon Nova Lite, NOT Claude Haiku (good catch).** Anthropic models on
   Bedrock need a first-time-use form + sometimes a Marketplace subscription → access delay
   risk on a deadline. **Amazon Nova models have simpler/near-instant access AND are more
   AWS-native** (better ex-AWS signal). Plan: dev on **free Gemini**, deploy on **Nova Lite**
   (discover the exact model ID at deploy, don't hardcode); Claude Haiku = optional if access
   clears in time. All behind the `ModelProvider` adapter, so it's a config swap.
3. **Privacy — DISABLE model-training on BOTH tools (do this before pasting any code).** Aivar
   forbids sharing the solution; consumer AI plans may train on your inputs. ChatGPT: Settings
   → Data Controls → turn OFF "Improve the model for everyone." Claude: Settings → Privacy →
   turn OFF model-improvement usage. Use only synthetic invoices/PII; never paste AWS keys/OTP/
   PAN/card data.
4. **Codex workspace path:** point Codex at the REAL folder `/Users/srisruthi/Aivar Project`
   (Codex was pointed at a missing `/Users/srisruthi/Documents/Aivar Project`). First action =
   clean baseline commit in the private repo.
5. **Humility on tool-comparison stats (conceded):** my earlier "Claude 67% cleaner / Codex 4×
   efficient" framing was too broad (vendor-adjacent benchmarks). METR found no statistically
   significant GENERAL advantage either way — treat the split as *workflow-surface* differences,
   not a ranking. Keep the role split (Claude=architecture/agents/review; Codex=IaC/tests/
   deploy) because it fits the surfaces, not because one model is "better."

## 4e. ⚠️ RUTHLESS PRIORITIZATION — the plan is still maximalist for ~2.5 nights
Codex's plan lists 15 local items + unit+property+contract+integration+LOAD tests + Playwright
+ Locust/k6 + Bandit/pip-audit/cfn-lint + ADRs + runbooks. **You will NOT finish all of that
solo in the time.** A comprehensive plan that doesn't ship loses to a finished smaller one.
Build in THIS order and stop-loss ruthlessly:
- **CRITICAL PATH (must ship, in order):** (1) 2-agent invoice workflow on free Gemini +
  typed MCP tools + free PII redaction; (2) **deterministic assurance state machine +
  Hypothesis property tests** — THIS is the core senior engineers scrutinize, protect its
  time; (3) evidence store (local, then DynamoDB) + 5-min reconciliation + ONE canary (PII);
  (4) the demo path GREEN→failure→AMBER/RED→repair→AMBER→verified-GREEN working locally;
  (5) deploy to AWS (Nova Lite) + `/healthz` + real logs; (6) README + 1 architecture diagram
  + PDF write-up (market comparison from our research) + 5–8 min demo-first video.
- **CUT FIRST if time is short (nice-to-have, not scored much):** load testing (Locust/k6),
  Playwright UI smoke tests, second canary (HITL), full security-scan suite (keep a basic
  `bandit`/`pip-audit`), extensive ADR set (keep ONE 1-page ADR), integration tests beyond
  the happy path, CloudFront (S3 static is enough).
- **Rule:** a working GREEN→AMBER→GREEN demo deployed on AWS with the property-tested engine
  beats every extra test tier. Don't gold-plate the tooling and run out of runway on the demo.

## 5. What I'd tell you in one breath
Codex's answer is 80% right and I'm keeping the 80% (extension-ready slice, stable contracts,
deterministic engine, cross-review, OIDC, budgets). The 20% I'm overruling is the Phase-1
stack: **build on plain Lambda + SAM + DynamoDB + EventBridge + a light MCP server + static
HTML + Haiku — not Strands/AgentCore-Gateway/Cognito/React/CDK.** Same extensibility, a
fraction of the risk, and it actually ships by Saturday. Extend *after* you submit, if at all.
