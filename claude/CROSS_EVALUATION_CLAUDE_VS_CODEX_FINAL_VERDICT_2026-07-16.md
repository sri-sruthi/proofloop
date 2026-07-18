# Cross-Evaluation: Claude's PS-4.3 (Vigil) vs Codex's PS-6.2 (ProofLoop) & PS-5.1 (AegisFlow)
*Jul 16, ~7pm. Read end to end: Codex's 2 dossiers + 2 source registers (Jul 16), my
market-research/decision doc + Vigil plan + Databricks-intel doc (Jul 16), my Jul 13
market-reconsideration + PS-7.1/9.1 plans. Aivar site claims independently verified.*

## What Codex got RIGHT (credit where due)
1. **ProofLoop's product thinking is genuinely excellent.** The false-green/false-red
   distinction ("zero events ≠ control working" AND "zero events ≠ control dead"), active
   control canaries, the explicit UNKNOWN evidence state, and replay-before-rollout are
   sharp, senior-level ideas. If this were a 2-3 week task, ProofLoop would be a serious
   contender for the win.
2. **Its Aivar grounding is better than mine was.** It pulled Aivar's actual site language
   — "Day 2 problem of AI, led by Governance & Integration," "No Black Boxes," "Production,
   Not Slides," customer-as-fifth-element, Velogent freight-invoice case studies. I
   verified these are real. Vigil's write-up must adopt this framing.
3. **Its "claims to avoid" discipline** (never claim first/only/no-competitor; never claim
   exactly-once) is exactly the honesty ex-AWS reviewers reward. Adopting wholesale.
4. **It killed its own PS-5.1 premise honestly** — AegisFlow's dossier opens by conceding
   the agent-firewall market is covered (AWS/Microsoft/Google/Cisco/PaloAlto/Lakera/
   Portkey/Cloudflare/Pipelock) and even Codex now ranks it #2. That matches my research.
   **PS-5.1 is eliminated by BOTH AIs independently. Close that door.**
5. **A real catch against my earlier PS-9.1 option:** Velogent already ships
   Block/Review/Approve HITL policies — PS-9.1 risks rebuilding Aivar's own feature.
   Downgrades 9.1.
6. **A fair softening of my whitespace claim:** Lakera "Agent Behavior Defense" (behavioral
   intent modeling) and classic fraud/abuse tooling are ADJACENT to PS-4.3. My write-up
   should name them as nearest neighbors — per-agent intent modeling and non-LLM abuse
   scoring — while noting neither does per-user, cross-session correlation for LLM apps.
   The whitespace claim survives; the phrasing gets more honest.

## Where Codex's recommendation BREAKS (the case against ProofLoop-as-specced)
1. **Scope vs the actual deadline — disqualifying.** ProofLoop's own "must-have vertical
   slice": a 3-agent Strands workflow on AgentCore Runtime + Gateway + Policy + Bedrock
   Guardrails + HITL + OTel/ADOT ingestion + EventBridge + SQS/DLQ + DynamoDB + S3 +
   React/TypeScript dashboard + Cognito + Terraform + GitHub-OIDC CI/CD + canaries + state
   machine + SLA incidents + tests incl. Hypothesis/Locust/Playwright. That is 2–4 weeks
   of work for an engineer who already knows AWS. Sri has ~2.5 nights and zero AWS
   background. Codex's OWN AegisFlow doc warns "do not attempt a general-purpose
   enterprise platform in two days" — then ProofLoop's must-have list is one. This is the
   exact overscope failure mode our CLAUDE_CODEX_WORKFLOW doc predicted for Codex output.
2. **Stacked dependency risk.** It builds ON AgentCore Runtime/Gateway/Policy + Strands —
   four unfamiliar managed services with their own IAM, quotas and setup friction. One
   blocked evening (model-access approval, region limits, Gateway config) sinks the
   timeline. Vigil deliberately rides plain Lambda + DynamoDB + Bedrock InvokeModel —
   boring by design, and boring is what ships by Saturday.
3. **The DS-fit score (9.5/10) is inflated by its own text.** ProofLoop's design says
   plainly: "ProofLoop should not use ML where a deterministic rule is more reliable."
   Its core is a deterministic state machine + evidence plumbing; the statistics
   (change-point detection, silence calibration) are garnish. In the interview Sri would
   be defending EventBridge retries, idempotency keys and DLQs — systems engineering, not
   her ground. Vigil's core IS the statistics: behavioral scoring, decay, threshold
   calibration, FPR control — her IoT-IDS work, transplanted.
4. **Market position is weaker than it looks.** ProofLoop's own market table concedes
   ServiceNow AI Control Tower, IBM watsonx.governance and OneTrust already do continuous
   AI governance/assurance; differentiation is a narrow slice (canaries, unknown-state)
   within an occupied category. PS-4.3 has NO product incumbent — 2026 research papers
   only. On the mandatory market-comparison section, Vigil's story is simply stronger.
5. **Codex's only argument against PS-4.3 is a label: "cybersecurity-focused."**
   Examined, it doesn't hold for Sri's actual objection. Her PS-3.2 objection was
   (a) crafting working injection attacks, (b) not wanting a security-engineering career
   lane. PS-4.3 requires neither: the "attacks" are scripted traffic patterns (paraphrased
   blocked prompts, sequential IDs) — no exploit engineering; the unit is Observability &
   Behavioral Monitoring; the discipline is trust-&-safety/abuse ANALYTICS — a recognized
   data-science field (fraud analytics), not security engineering. And she herself
   re-opened tonight liking the WAF — a Unit-5 security PS — so the aversion was to
   out-of-depth interviews, not to the word "security." Vigil interviews on HER depth.

## Self-critique (what my docs must fix — actioned in the Vigil plan v2 additions)
- Missing Aivar-site grounding (Day-2 / No-Black-Boxes / fifth-element / Velogent-style
  workload) → adopted; alert cards framed as "No Black Boxes" evidence.
- Whitespace phrasing too absolute → name Lakera + fraud-analytics as nearest neighbors.
- Missing: honest-claims list, self-monitoring ("monitor the monitor"), AWS budget alarm +
  teardown script, GitHub-OIDC (no long-lived AWS keys in CI), demo-first video script
  discipline → all adopted from Codex. This is cross-model review working as intended.
- My PS-9.1 plan is now downgraded (Velogent overlap, per Codex's catch).

## Scores under the REAL constraint (deployed + explained + video'd by Sat night)
| | Whitespace | DS/interview fit | Finishable by Sat | Aivar-fit | Demo punch |
|---|---|---|---|---|---|
| PS-4.3 Vigil | **5** | **5** | **4** | 4.5 | **5** |
| PS-6.2 ProofLoop (as specced) | 3.5 | 2.5 | **1.5** | **5** | 4 |
| PS-6.2 descoped to PS-6.2-core | 3.5 | 2.5 | 3.5 | **5** | 4 |
| PS-5.1 AegisFlow | 1.5 | 3 | 2.5 | 4 | 4.5 |

## FINAL VERDICT
**Build PS-4.3 — Vigil (Cross-Session Adversarial Pattern Detector), upgraded with
Codex's best ideas** (Aivar framing, honest-claims discipline, self-monitoring, budget
alarm/teardown, OIDC CI, softened-but-intact whitespace claim, and a Velogent-style
support/invoice agent as the governed demo workload).

It is the only option that is simultaneously: genuine market whitespace, algorithmically
tough, defended entirely on Sri's own expertise, and honestly finishable — deployed on
AWS with a vivid demo — by Saturday night. ProofLoop is a better *product idea for a
team with three weeks*; Vigil is the better *submission for this candidate with three
nights.* The evaluators grade what ships.

**Escape hatch (only if Sri, reading ProofLoop, feels "THIS is the one I want to defend"):**
a strictly descoped PS-6.2-core — compliance record + 5-min sync engine + ONE canary +
timeline + green/amber/red with UNKNOWN, on plain Lambda/DynamoDB, NO AgentCore/Strands/
React/Cognito — is feasible. But it trades away her DS interview story, and I don't
recommend the trade.

---

# ROUND 2 ADDENDUM (Jul 16, later) — I CHANGE MY RECOMMENDATION to scoped PS-6.2

Codex replied with a *scoped* ProofLoop and a sharper critique. Re-deriving from Sri's
OWN stated goals this session — not from my prior pick — I now think **Codex is right.**
This is a flip on new evidence + a removed objection + goal-realignment, not capitulation.

## The new fact that moved me (verified Jul 16)
AWS AgentCore **Optimization** (2026) surfaces "failure, intent, and trajectory insights
across hundreds of sessions" (https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-bedrock-agentcore-new-optimization-capabilities/).
Its PURPOSE is agent quality (auto-improve prompts/tools), NOT per-user adversarial
detection — so Vigil's angle isn't identical. BUT: this is the SECOND AWS release adjacent
to my pick (Policy→WAF, Optimization→cross-session). Vigil's whitespace is now a fine
distinction, not a clean gap. Same failure mode I used to KILL PS-5.1 now applies to 4.3.

## Codex's 5 points, honestly scored
1. **Vigil is fundamentally cybersecurity — CONCEDED.** I called it "fraud analytics = DS";
   that was rationalization. It models adversaries, campaigns, SOC threat cards. Sri has
   said repeatedly she is NOT interested in cybersecurity. This is a values-mismatch I
   talked around.
2. **Whitespace unsafe — CONCEDED (partial).** Narrowed by AgentCore Optimization; still
   some differentiation but no longer "nothing exists."
3. **Eval would be heavily scrutinized — CONCEDED, and it's serious.** Vigil's credibility
   rests entirely on a false-positive story. In ~2.5 nights, scripted cohorts + one benign
   user can't answer the questions ex-AWS reviewers WILL ask (multilingual, repeat legit
   users, identity rotation, coordinated accounts, evasion, drift). The very thing that
   makes Vigil impressive (calibration) is the hardest to make credible in the time and the
   most exposed to expert cross-examination.
4. **Production omissions — partially true; applies to BOTH.**
5. **Doesn't satisfy the agentic-AI objective — CONCEDED, and decisive.** THIS session Sri
   said she wants to "find agentic AI use cases and BUILD a solution." Vigil's agent is a
   mock target; the system is a detector. Scoped ProofLoop is a genuine 2-agent workflow
   (extraction + reconciliation + HITL) — it IS the agentic build she asked for.

## What Codex fixed
My core objection to PS-6.2 was overscope (2–4 weeks). Codex removed it: scoped to 2 agents,
4 control monitors, 2 canaries, deterministic 5-min reconciliation, plain
Lambda/DynamoDB/EventBridge, static dashboard — NO AgentCore/Strands/Cognito/React. That is
buildable in the window, and its deterministic core is MORE demonstrable under scrutiny than
Vigil's statistical FPR.

## Where I hold Codex accountable (so the decision rests on the right axis)
Whitespace is NOT ProofLoop's advantage — its category is arguably MORE occupied (ServiceNow
AI Control Tower, IBM watsonx.governance, OneTrust; AgentCore Observability). Neither option
has clean whitespace. So do NOT choose on novelty. Choose on FIT — and on fit with Sri's
actual goals, scoped ProofLoop wins: it's genuinely agentic (her stated goal), non-security
(her stated preference), Aivar-aligned (Day-2/Velogent), extends her real resume (multi-agent
+ evaluation + APIs + monitoring, not "another anomaly detector"), and its deterministic core
survives interrogation better than a rushed calibration story.

## REVISED VERDICT
**Build the SCOPED PS-6.2 — ProofLoop.** Vigil drops to fallback. The single condition to
pick Vigil instead: Sri decides she WANTS to present as a data-science / anomaly-detection
candidate and lead the interview with calibration. She has said the opposite. So: ProofLoop.

Honest note to Sri: I argued hard for Vigil and I was wrong on the points that count for
YOUR goals. Changing my answer when the evidence changes is the behavior you want from me,
especially on a decision this important. The two are close — but scoped ProofLoop is the
better submission for the engineer you're trying to be seen as.

--- END OF CROSS-EVALUATION ---
