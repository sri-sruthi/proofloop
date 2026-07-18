# AegisGate (Codex direction) + Verified Intel + Synthesis Recommendation
*2026-07-12 · Third input to the problem-statement decision. Read with `DECISION_BRIEF.md`.*

A second AI (Codex 5.6 "ultra") independently recommended **PS-5.1 — The Agent WAF**,
branded **AegisGate**, with a very thorough build spec. This document (1) records that
direction faithfully, (2) adds the company/competitive facts I verified by web research,
(3) gives my honest assessment of where Codex is right and where I'd push back, and
(4) proposes a synthesis. Nothing here deletes `PROJECT_PLAN.md` or
`PROJECT_PLAN_PS3.2_BehavioralDetector.md`.

---

## 1. The Codex AegisGate direction (faithful summary)

**Pick PS-5.1.** Build an MCP-native Agent Action Firewall deployed in the customer's
AWS account, sitting between an agent and its tools, enforcing policy before any real
action executes.

**Demo workload (excellent, reusable):** a bounded customer-support & refund agent.
Customer asks about a refund → agent retrieves policy via RAG → accesses customer data
via MCP tools → may update a ticket, issue a refund, send email, write memory →
AegisGate intercepts every proposed action → allow / block / review / shadow → everyone
gets a clear explanation + audit trail. One scenario demonstrates: indirect prompt
injection in a retrieved doc, cross-customer data block, over-authority refund, external
email needing approval, refund-before-verification, tool-call loop, sensitive data kept
out of memory, and normal requests flowing unimpeded.

**Differentiation vs AWS AgentCore:** provider-neutral (Bedrock + Anthropic + others),
drop-in MCP reverse-proxy, customer-owned code/deploy, portable versioned+replayable
policy, least-privilege suggestions from observed traffic, developer/reviewer/customer
explanations, built-in adversarial eval harness, combined action+loop+cost+memory
protection, AgentCore-compatible but not dependent.

**Architecture:** Bedrock agent → Policy RAG (Bedrock Knowledge Bases + S3 Vectors) →
AegisGate (deterministic policy engine: rate/schema/scope/sequence) → allow to MCP tools
/ HITL queue / block+shadow evidence; DynamoDB state; OTel→CloudWatch; React dashboard;
Cognito auth; API Gateway; Lambda; Step Functions for durable HITL; SQS+DLQ; SAM IaC;
private GitHub Actions with OIDC, canary + alarm rollback.

**Systematic workflow:** customer charter → threat model + ADRs → **evaluation harness
before features** (~50 tasks, deterministic graders, capability vs regression suites) →
thin vertical slice → required PS-5.1 features → production hardening (idempotency,
retries+jitter, circuit breakers, DLQ, `/health/live`+`/health/ready`, loop/token/cost
caps, immutable version IDs) → RAG+memory → DS/monitoring layer (deterministic boundary,
DS only calibrates) → release engineering (10 CI gates) → acceptance targets.

**Non-goals V1:** no EKS, no NAT/VPC unless needed, no multi-agent swarm, no FM training,
no OpenSearch, no LLM deciding hard authorization, no server-initiated MCP
sampling/streaming, no storing hidden chain-of-thought.

---

## 2. Verified facts (my web research, 2026-07-12)

### About Aivar (this materially changes the calculus)
- Founded by **four ex-AWS engineers** (Kousik Rajendran CEO; Praveen Jayakumar; Ashwin
  Ram; Aadarsh Ayyappan). **AWS Advanced Tier Partner**, L400 depth, healthcare/fintech/
  retail. $4.6M seed (Sorin Investments, Bessemer). **80+ customers**, pilot→production.
- Built on **Amazon Bedrock** (Claude, Amazon Nova, Meta Llama). Homepage tagline:
  **"Governed Agentic AI Stack for Enterprise."**
- Productized accelerators: **Convogent** (voice AI), **Velogent** (agentic automation),
  **Kubogent** (ML Ops). → They value **both** agentic-governance engineering **and**
  production ML/DS rigor.
- Sources: [Bessemer](https://www.bvp.com/news/realizing-ai-for-global-enterprises-with-aivar),
  [YourStory](https://yourstory.com/2026/01/ai-services-startup-aivar-raises-46m-production-ready-enterprise-solutions),
  [AWS Partner listing](https://partners.amazonaws.com/partners/001aq000007wYZxAAM/Aivar%20Innovations%20Private%20Limited),
  [aivar.tech](https://www.aivar.tech/).

### About the competition (this is the key risk for PS-5.1)
- **AWS Bedrock AgentCore Policy is GA (March 3, 2026):** Cedar-based, intercepts all
  agent traffic through AgentCore Gateway, evaluates each tool call before execution,
  supports **LOG_ONLY (shadow) and enforce** modes. This is **PS-5.1's exact feature
  set, from AWS itself.** The ex-AWS/Bedrock founders know it intimately.
- Sources: [AgentCore Policy docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html),
  [AWS Security blog: why Cedar](https://aws.amazon.com/blogs/security/why-policy-in-amazon-bedrock-agentcore-chose-cedar-for-securing-agentic-workflows/),
  [AWS News: AgentCore evals + policy](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/).

### About AWS guidance (useful for any option)
- **AWS Well-Architected Agentic AI Lens** (2026): decompose into **bounded agents** with
  declared scope/limits/authority; make every action **observable end-to-end**; **bounded
  autonomy**. Cite this in the PDF regardless of chosen PS.
  [Agentic AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentic-ai-lens.html),
  [design principles](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/design-principles.html).

### Tooling currency (Codex was right; keep these)
- Claude Code custom slash commands are now **Skills** (`.claude/skills/<name>/SKILL.md`,
  still invoked as `/name`); side-effecting skills set `disable-model-invocation: true`.
- Use **OpenTelemetry/ADOT** for new tracing (X-Ray SDK/daemon in maintenance mode).
- Don't anchor monitoring on **SageMaker Model Monitor** (closing to new customers
  ~July 30, 2026); use versioned baselines + scheduled Lambda/Glue + CloudWatch.
- MCP authorization: OAuth 2.1, audience-bound tokens; never blindly forward the client
  token downstream.

---

## 3. My honest assessment of the Codex recommendation

### Where Codex is clearly right
- The **bounded support-agent demo workload** is superb and I'd adopt it wholesale — for
  *either* PS. One scenario, many governance moments, objectively gradable.
- The **engineering discipline** (eval-before-features, failure-mode matrix, idempotency,
  acceptance targets as *targets not claims*, currency of tooling) is exactly what
  ex-AWS bar-raisers respect. This is reusable gold.
- The **company-alignment argument** is real: Aivar is AWS/Bedrock to the core, and a
  production AWS-native governance product speaks their language.

### Where I push back
1. **AWS-alignment cuts both ways.** Because AgentCore Policy already does PS-5.1's job
   (GA'd 4 months ago) and the founders built AWS, a PS-5.1 build is judged against an
   incumbent they know cold. Codex admits a "basic AWS-only WAF would not be innovative"
   and escapes only via *subtle* differentiation (portable/provider-neutral/explainable)
   — which demands strong **systems engineering**, the one area Sri Sruthi's resume does
   not yet evidence. High ceiling, higher scrutiny risk.
2. **Codex downgraded PS-3.2 for exactly Sri Sruthi's strengths.** It ranked PS-3.2 #4
   citing *"harder to prove generalization; high false-positive risk with limited data."*
   But her IoT-IDS project is *about generalization* (domain adaptation, F1 0.999→0.387→
   0.722) and her deepfake/clinical work is *about calibration and false-positive
   control*. Codex optimized for the best abstract product, not for *this candidate's*
   defensibility. The cited weakness is her home turf.
3. **Differentiation from the incumbent is actually easier with PS-3.2.** AgentCore does
   deterministic Cedar policy + content guardrails; it does **not** do behavioral/ML
   detection of *successful* injection by watching what the agent does next. That niche
   is both more novel vs Aivar's known stack **and** on the candidate's turf. And Aivar's
   **Kubogent (ML Ops)** accelerator shows they value exactly this DS rigor.

### Net
Codex picks the best *product*. For *this candidate against this company*, the
best-defensible, most-differentiated center of gravity is the **behavioral detector**,
wrapped in Codex's production apparatus.

---

## 4. The synthesis I recommend (best of both)

**"Sentinel-on-AegisGate": a bounded support agent on AWS, governed by a *minimal*
deterministic action boundary, with a *behavioral injection detector* as the signature
innovation.**

- **Core scenario:** Codex's bounded customer-support & refund agent (Bedrock/Claude +
  MCP tools + policy RAG). Adopt as-is.
- **Table-stakes layer (thin PS-5.1):** a small deterministic boundary — data-scope,
  tool-sequence, and irreversible-action rules only (3 rule types, not the full WAF).
  Simple, objectively testable, gives the AWS-native production credibility Aivar wants
  and prevents the demo attacks. Runs in shadow→enforce.
- **Signature layer (PS-3.2, the differentiator):** the behavioral baseline + multi-
  signal anomaly detector that catches a *successful indirect injection* by the agent's
  changed behavior, within one turn, with a calibrated threshold and documented FPR.
  This is your resume made manifest, and it's the thing AgentCore can't do.
- **Everything else** (eval harness, failure-mode matrix, observability, CI gates,
  customer-first traceability, cost caps, one-command deploy/teardown, PDF diagrams) is
  shared — take Codex's apparatus verbatim.

**Why this wins for you specifically:**
- Objectively-testable production system (Aivar/Codex requirement) ✔
- Genuinely differentiated from AgentCore, which they know cold ✔
- Deep-scrutiny questions land on your published strengths (generalization, calibration,
  drift) ✔
- Honors *both* Aivar accelerators: Velogent (agentic governance) **and** Kubogent (ML) ✔

**Scope discipline (so a solo 5–7 day build stays finishable):** keep the deterministic
layer deliberately small (3 rule types); invest the differentiation depth in the
detector. Don't build a full WAF *and* a full detector — that's the trap. The detector
is the headline; the deterministic rules are supporting cast.

---

## 5. Reusable regardless of which PS you pick

Take these from Codex no matter what:
1. The bounded support-agent demo scenario.
2. Eval harness *before* features; grade environment outcomes, not the agent's own words.
3. Failure-mode matrix (fail-closed on writes/money/external comms; degraded+audited on
   reads; never silently allow on policy-service failure).
4. Acceptance targets framed as *targets to measure*, never pre-measurement claims;
   never say "production-proven" for a demo.
5. Currency: Skills (not slash commands), OTel/ADOT (not X-Ray), avoid SageMaker Model
   Monitor, MCP OAuth 2.1 token hygiene.
6. Required diagram set (C4 context, container, AWS deployment, MCP sequence, policy-
   decision flow, data-flow/trust-boundary, HITL state machine, CI/CD+rollback).
7. Customer-need → product-decision → evidence traceability table.
8. Cite the AWS Well-Architected **Agentic AI Lens** (bounded agents, end-to-end
   observability) in the PDF.
9. Honest "what weakens the submission" list: no EKS for tiny workloads, no needless
   multi-agent swarm, no framework without demonstrated need, no LLM deciding hard authz,
   no public GitHub, no unverified accuracy/cost claims.

---

## 6. The three options on the table

| | PS-5.1 (Codex/AegisGate) | **Synthesis (recommended)** | PS-3.2 (pure detector) |
|---|---|---|---|
| Center of gravity | Deterministic action firewall | Detector + thin deterministic boundary | Behavioral detector |
| Best product / cold pitch | ★★★ | ★★★ | ★★☆ |
| Differentiated vs AgentCore | ★☆☆ (competes head-on) | ★★★ | ★★★ |
| Matches Sri Sruthi's resume | ★☆☆ | ★★★ | ★★★ |
| Interview defensibility | ★★☆ | ★★★ | ★★★ |
| Solo-build finishability (5–7d) | ★★☆ | ★★☆ | ★★★ |
| Honors both Aivar accelerators | ★★☆ (Velogent) | ★★★ (both) | ★★☆ (Kubogent) |

My suggestion: **the synthesis**, or **pure PS-3.2** if you want the safest, most
finishable scope. Straight PS-5.1 is the riskiest for *you* specifically, despite being
the best abstract product — because it competes head-on with a product the evaluators
built, on engineering terrain your resume doesn't yet cover.
