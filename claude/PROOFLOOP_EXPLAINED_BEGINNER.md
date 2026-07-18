# ProofLoop, Explained From Scratch (beginner-friendly)
*Jul 17 2026. For Sri to fully understand + explain the project in the interview. Plain
language + analogies. Covers: what we're building, how it maps to every PS-6.2 requirement,
each tech-stack piece, and why the assurance decision is deterministic (with evidence).*

---

## PART 1 — What are we actually building? (and the data-science analogy)

### The problem in one sentence
An enterprise deploys an AI agent with safety **controls** — it redacts personal data (PII),
it has guardrails, it logs everything for audit, and it asks a human before big actions. On
Day 1 someone ticks "all controls ON." But months later a control can **silently stop
working** — still marked "enabled" in config, but not actually running (a code change bypassed
it, a service broke, a filter is misconfigured). **Nobody notices** until an auditor or an
incident finds out the agent was ungoverned for weeks. That's a *false sense of security*.

### What ProofLoop does (one sentence)
ProofLoop **continuously proves whether each control is actually working right now** — using
fresh evidence from the running system plus **active tests it fires itself (canaries)** — and
if it *can't* prove a control is working, it says **AMBER / UNKNOWN**, never a false "green."

Think of a **smoke detector that tests itself.** A normal detector might be dead for a year
and you'd never know. ProofLoop is a detector that presses its own test button every 5 minutes
and lights up amber the moment it can't confirm it still works.

### The data-science analogy you asked for
You know the DS loop: **collect data → clean → feature-engineer → model → evaluate.** Here's
ProofLoop in those exact terms:

| DS step | In ProofLoop |
|---|---|
| **Collect data** | We collect **evidence**: telemetry from the running agent (did the guardrail fire? was the PII masked? did the human approve?) + **canary results** (we inject synthetic test inputs and watch what the controls do). |
| **The dataset we create** | Synthetic invoices, purchase orders, and deliberately-broken **failure scenarios** (guardrail disabled, PII leaked, approval skipped). This is *our* dataset — we generate it. |
| **Feature engineering** | We turn raw evidence into **signals**: freshness (how recent?), coverage (did every required path emit evidence?), confidence, and control-event *rates* over time. |
| **The "model"** | Deliberately **NOT** an ML model for the final verdict (see Part 4 — it's a deterministic rules engine). BUT there **is** a data-science layer that computes the calibrated signals above (change-point detection on event rates, calibrated "silence" thresholds, confidence scoring). **The DS lives in the signals; the verdict is deterministic.** |
| **Evaluate** | Our **evaluation harness**: we measure precision / recall / **false-positive rate** of ProofLoop's own control-health detection against the labelled failure scenarios. (This is *your* evaluation background, front and centre.) |

So concretely, **what WE build**: (a) a small **agent being governed** (the 2-agent invoice
workflow — the "patient"); (b) the **synthetic dataset** (invoices + failure cases); (c) the
**evidence pipeline** that instruments the agent; (d) the **assurance engine** that turns
evidence into a health verdict; (e) the **evaluation** that proves the engine is accurate.

### Who is the customer, and what are we solving for them?
The **customer** = the enterprise running the AI agent (e.g., a logistics company whose agent
processes invoices — exactly Aivar's Velogent use case). Their role in the product:
- They **choose** which controls matter and set the thresholds and response policy.
- They **read** the dashboard (a plain green/amber/red per control + a 7-day timeline).
- They can **export and independently verify** every decision ("No Black Boxes" — Aivar's motto).
**What we solve for them:** we close the gap between *"the control is configured"* and *"the
control is provably working right now,"* so they're never falsely told they're protected.

---

## PART 1b — The THREE datasets (this is what makes it a real DS project, not a dashboard)
*Adopted from Codex's Jul-17 elaboration — it's a genuine improvement and directly answers
"what's the data?" + resolves the "will I be pigeonholed as guardrails?" worry. The data
science is REAL only if these datasets, labels, calibration and evaluation are real artifacts.
We build all three.*

1. **Business-workload dataset** — synthetic invoices + POs + vendor records + approval rules,
   with **ground-truth** extracted fields and expected action. Cases: correct invoice, wrong
   total, duplicate, missing PO, unknown vendor, changed bank account, high-value (needs
   review), inconsistent tax, malformed doc. → used to evaluate the AGENTS (extraction F1,
   reconciliation accuracy, tool-selection, hallucination rate).
2. **Runtime-evidence dataset** — the structured events every control/agent emits (control ID,
   eligible-request count, invocation count, allow/block/redact/review result, versions, trace
   ID, timestamps, errors, canary ID, telemetry-completeness). **This — not raw invoices — is
   ProofLoop's main operational dataset.**
3. **Assurance-evaluation dataset** — we deliberately **inject known failures** (guardrail
   disabled, bypassed-on-one-route, collector outage, delayed/duplicate/out-of-order events,
   schema change, canary-infra failure, HITL-configured-but-not-enforced, partial/full
   recovery, cross-tenant attempt). Because WE inject the fault, we know the **ground-truth
   status** → so we can compute real **recall / false-alarm rate / calibration**.

**Engineered features (concrete, defensible):**
```
execution_coverage = guardrail_invocations / eligible_requests
canary_pass_rate    = successful_canaries / scheduled_valid_canaries
evidence_freshness  = now - last_valid_evidence_time
compliance_debt     = status_severity × duration_of_degraded_state
```
**DS methods:** interpretable statistical monitoring (**EWMA / CUSUM / rate-ratio** on
traffic-normalized control rates) to catch sudden changes; **calibrated confidence** (measure
how often an evidence-combination actually matches ground truth, then calibrate — NOT an
arbitrary weighted "AI score"); **evaluation harness** (pandas + scikit-learn + local MLflow
to track eval runs, dataset versions, metrics). Two evaluation systems, both first-class:
(a) **agent-workload eval** (extraction F1, reconciliation accuracy, hallucination, cost);
(b) **assurance eval** (failure-detection recall, false amber/red rate, MTTD, coverage,
transition accuracy, recovery time, calibration). This is the 30%-data-science of the project.

**⚠️ Build caveat (unchanged):** ADOPT the DS tooling above (pandas / scikit-learn / local
MLflow / JSONL-Parquet datasets — lightweight, local, and they ARE the DS showcase). But keep
the DEPLOYMENT stack lean per §4e: Codex's tech table re-lists React + Cognito + CloudFront +
Locust/k6 + Playwright — those stay **cut-first / nice-to-have**. Static HTML dashboard,
API-key auth, SAM. The DS depth is critical path; the heavy UI/auth/load tooling is not.

## PART 2 — How our project maps to EVERY point in the PS-6.2 statement
Aivar's PS-6.2 "Runtime-to-Compliance Bridge" lists required pieces. Here's ours, one-to-one,
plus where we go **beyond** the minimum (which is how you score above other candidates):

| PS-6.2 asks for… | What ProofLoop builds | Beyond the minimum |
|---|---|---|
| **Compliance record** (guardrails_active, last_violation_timestamp, pii_redaction_enabled, audit_logging_enabled, hitl_configured, status green/amber/red) | Exactly these fields per agent in DynamoDB | + evidence **freshness, coverage, confidence**, versions, reason codes |
| **Runtime telemetry collector** (poll or webhook from the agent's guardrail + audit logger) | Evidence collector: the agent emits events → SQS → collector → stored | + **active canaries** that *test* the control, not just passively listen |
| **Sync engine** (update every 5 min; if a check that should be active produced zero events for 24h, flag it) | EventBridge fires the deterministic evaluator every 5 min | + **traffic-aware**: zero events with zero traffic ≠ broken; we don't false-alarm |
| **Compliance status timeline** (7-day history with the triggering event per change) | Append-only status-transition log, rendered as a timeline | + each transition cites the exact **evidence + rule + version** that caused it |
| **Success: reflects active guardrails when working** | GREEN only when fresh evidence + a passing canary prove it | + explicit **UNKNOWN** so we never fake green on missing data |
| **Success: simulated failure → amber in 24h, red in 48h** | State machine with configurable windows + an **injectable virtual clock** so we demo 24/48h in seconds | honest: video discloses the accelerated clock |
| **Success: timeline shows transitions + timestamps** | The 7-day timeline endpoint + dashboard | — |
| **Success: re-enabling restores green next sync** | Recovery path: **red → amber → (fresh canary passes) → green** | + green is restored **only after fresh proof**, never a manual toggle |
| **Bonus: compliance SLA → auto-incident if amber/red too long** | Incident record + customer response when SLA breached | + smallest **reversible** response, customer-configurable |

**The signature idea (what makes it *yours*, not a generic dashboard):** *configuration alone
can never produce green; missing evidence is UNKNOWN not green; canaries actively test the
real control path; a repaired control stays amber until fresh evidence re-proves it.*

---

## PART 3 — The tech stack, each piece explained simply (why + how)
Think of it as a restaurant: the **agents** are the cooks, the **controls** are the food-safety
rules, and **ProofLoop** is the health inspector who keeps checking the kitchen.

| Piece | What it is (plain) | Why we use it / how it works here |
|---|---|---|
| **Python + FastAPI** | A language + a tool to build web APIs | FastAPI is how the outside world talks to ProofLoop (send an invoice, ask "what's the status?"). It turns Python functions into web endpoints. |
| **Pydantic** | A data-shape validator | Makes sure every piece of evidence/message has the right fields and types — catches bad data at the door. |
| **The 2 agents** (extraction + reconciliation) | Two small LLM-powered workers with different jobs | Extraction reads an invoice → structured fields; Reconciliation checks it against a purchase order. Two agents = a real **multi-agent** system with different *authority* (a current AI trend, and Aivar's Velogent shape). |
| **MCP server** (Model Context Protocol) | A standard way for an AI agent to call "tools" | Our agents call typed tools (e.g., "record payment", "get evidence") through MCP — the 2026 industry-standard tool layer. Keeps tool calls typed and inspectable. |
| **`ModelProvider` adapter** | A swappable socket for the AI model | Lets us run **free Gemini** while building and **Bedrock Nova** in the cloud, by changing one line. This is why cost/vendor is a config choice, not a rewrite. |
| **Amazon Bedrock (Nova Lite)** | AWS's service to call AI models | The real LLM behind the agents in the deployed version. Nova is AWS's own model → instant access (Anthropic models need an approval form), and AWS-native (good for ex-AWS reviewers). |
| **Guardrails / PII redaction** | A filter that masks personal data | Blocks/masks PII in inputs & outputs. In the cloud = Bedrock Guardrails; while building = a **free library (Presidio/regex)** doing the same job. This is one of the *controls* ProofLoop watches. |
| **AWS Lambda** | Code that runs only when called (serverless) | Runs our Python with **no server to manage** and $0 when idle — you pay per request (and free-tier covers demo scale). Perfect for a 5-min-cycle app. |
| **API Gateway** | The front door to Lambda on the internet | Gives our Lambda a public HTTPS URL, handles auth/throttling. |
| **DynamoDB** | A fast NoSQL database | Stores the compliance records, evidence, and the append-only transition history. Serverless, free-tier friendly, handles concurrent writes safely. |
| **EventBridge Scheduler** | A cloud alarm clock | Fires the assurance evaluator **every 5 minutes** automatically — no server sitting idle. This *is* the "sync engine every 5 min" the PS asks for. |
| **SQS + DLQ** | A queue + a safety net | Evidence events line up in the queue (SQS) so nothing is lost under load; anything that fails repeatedly drops into the Dead-Letter Queue (DLQ) so you can see it, not lose it. |
| **The assurance state machine** | The rules engine that decides green/amber/red | The brain. Deterministic (Part 4). Takes evidence + signals → outputs an auditable verdict. |
| **Canary runner** | A tester that fakes a known input | Sends a synthetic invoice with fake PII and checks it got masked — *actively proving* the control works, not just hoping. |
| **Static dashboard (HTML/JS on S3)** | A simple web page | Shows each control's colour + the 7-day timeline. Plain HTML (no React) = fast to build, cheap to host. |
| **AWS SAM** | Infrastructure-as-Code | One config file that creates all the AWS pieces with **one command** (`sam deploy`) — and `sam delete` tears it down. This is the "automated deployment scripts" the task requires. |
| **GitHub Actions + OIDC** | Automated build/test/deploy pipeline | On every push it runs tests and can deploy. **OIDC** = it logs into AWS with a short-lived token, so **no AWS password is ever stored** in GitHub (a security best practice reviewers look for). |
| **pytest + Hypothesis** | Testing tools | pytest runs normal tests; **Hypothesis** throws hundreds of random cases at the state machine to prove the **invariants** (e.g., "stale evidence can NEVER show green") — this is what senior engineers scrutinise. |
| **The 8 adapter interfaces** | Swappable sockets for every external thing | ModelProvider, EvidenceRepository, WorkQueue, Clock, etc. They're why we build locally now and bind AWS later, and why Phase-2 (AgentCore) is a swap, not a rewrite. |

---

## PART 4 — Why is the assurance decision DETERMINISTIC? (your best question)

### First, clear up a confusion
"Deterministic" here does **not** mean the *guardrails* are simple. It means the part of
ProofLoop that decides **green / amber / red** is a **rules engine, not an LLM.** The
guardrails/controls it *watches* can be as smart as you like. We're talking about the **judge**,
not the thing being judged.

### Why the judge must be deterministic (this is best practice, not a shortcut)
A compliance verdict has to be **reproducible, auditable, and explainable** — the same inputs
must always give the same answer, and you must be able to point to *why*. LLMs are the opposite
of that, and 2026 research is blunt about it:
- **LLM-as-judge is unreliable for decisions:** across 8 studies (June 2026), *identical prompts
  disagree like coin flips*, and frontier models exceed **50% error on bias tests** — they
  prefer longer, "authoritative-looking" answers regardless of truth. Fine for rough scoring,
  **legally insufficient for compliance.**
- **Industry does governance deterministically on purpose:** AWS **Cedar** / AgentCore Policy
  and **OPA (Rego)** are deterministic engines — "the same principal, action, resource and
  context always produce the same decision." Enterprises deliberately **decouple the decision
  from the LLM** to move from *"hoping the agent behaves"* to *"enforcing boundaries."* Cedar
  evaluates in **<0.1 ms** and is *mathematically analysable* — an LLM is neither.

So if *ProofLoop* used an LLM to decide compliance, it would be circular and fragile: an
unreliable model judging whether your safety nets work. That's exactly what you must not ship.

### "But isn't a rules engine the bare minimum?" — the important nuance
You're right that *a plain if/else state machine, alone,* would be unimpressive. **The
sophistication isn't in the verdict — it's in the EVIDENCE and SIGNAL layer that feeds it.**
The architecture is:

> **Data science computes calibrated signals → the deterministic engine makes the auditable
> verdict from those signals.**

The intelligence lives in the signals:
- **Active canaries** (we *test* the control, not just listen) — the clearest innovation.
- **Explicit UNKNOWN state** — "no evidence" ≠ "healthy"; missing/stale data → amber, never green.
- **Traffic-aware silence detection** — zero guardrail events with zero traffic is fine;
  with traffic it's a red flag. Distinguishing these needs a calibrated threshold.
- **Freshness / coverage / confidence scoring** on evidence.
- **Change-point detection** on control-event rates (your IoT-IDS / drift muscle) to catch a
  control *degrading*, not just fully dead.
- **Calibrated false-positive control** (your calibration muscle) so the dashboard is trusted.

This is exactly how **safety-critical systems** are built: use ML/statistics for *perception*
(reading messy signals), use *deterministic logic* for the *safety decision* (so it's provable).
A self-driving car uses ML to see, but a deterministic rule to decide "emergency-brake." Same
pattern. The determinism is a **feature** (trust, auditability, "No Black Boxes"), and the data
science is where you show depth.

### The best approach (what we build)
1. **Verdict = deterministic** rules/state-machine (auditable, reproducible, Cedar/OPA-style).
2. **Signals feeding it = the data-science layer** (canaries, calibration, change-point,
   confidence/coverage, FPR control) — *this* is where the sophistication and your DS identity live.
3. **LLM used only for extraction + plain-English explanation of a decision — NEVER the verdict.**
4. Property-test the invariants (Hypothesis) so "stale can't be green," "red can't jump to
   green," etc. are provably true.

That combination — a provable deterministic core *plus* a calibrated data-science signal layer
*plus* active canaries — is well above "bare minimum," and it's the honest, defensible design
senior ex-AWS engineers will respect.
