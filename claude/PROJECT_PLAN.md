# AegisGate — The Agent WAF
## Aivar Innovations AI Governance Task · Full Project Plan
**Chosen problem statement: PS-5.1 "The Agent WAF" (Unit 5 — Agentic AI Security)**
*Plan drafted 2026-07-12 · Author: Sri Sruthi (with Claude Code)*

---

## 1. The Decision

**Build PS-5.1: The Agent WAF** — a policy-enforcing proxy between AI agents and their
tools that inspects, filters, and logs every tool invocation in real time — implemented
as an **MCP-native gateway**, deployed on **AWS free tier**, governing **real
Claude-powered agents also running on AWS**.

### Why PS-5.1 wins

1. **It is the exact center of the industry right now.** The "control plane between
   agent and tools" is *the* 2026 category:
   - Gartner: 40% of enterprise apps will embed task-specific AI agents by end of 2026
     (up from <5% in 2025).
   - McKinsey 2026 AI Trust Maturity Survey (~500 orgs): ~two-thirds cite security and
     risk as the #1 barrier to scaling agentic AI.
   - Citrix launched an MCP Gateway in July 2026; Microsoft shipped an open-source
     Agent Governance Toolkit at the action layer.
   - AWS's newest flagship, **Bedrock AgentCore**, just GA'd exactly this pattern:
     guardrails evaluated *at the gateway perimeter, outside the agent's code*. We are
     building the same architecture AWS itself just bet on, at a scale we can finish.

2. **The framing is irresistible to ex-AWS founders.** "AWS WAF, but for agent tool
   calls" is a one-sentence pitch they will viscerally get. The write-up maps our
   design to the AWS Well-Architected Framework pillars — their native language.

3. **Maximum trend coverage in one coherent system.** Implementing the proxy as an MCP
   gateway gives us MCP + agentic AI + guardrails + observability + policy-as-code +
   HITL in one project, nothing stapled on.

4. **Crisply demoable success criteria** for the 5–8 minute video: rate limit fires,
   injection blocked, out-of-scope access blocked, sequence rule enforced, dashboard
   updating live. Binary pass/fail demos are what senior reviewers trust.

5. **Timely regulatory hook:** EU AI Act high-risk enforcement begins **August 2026**.
   Audit-grade records of agent actions become a hard requirement. The PDF opens here.

### Runners-up considered and rejected

| PS | Why not |
|---|---|
| PS-1.2 MCP Server Risk Scanner | Very trendy but narrower — mostly a scanner + report, less of a "living system." We keep its spirit (MCP awareness) in the gateway. |
| PS-3.1 The Action Guardrail | Nearly the same idea, weaker framing, no dashboard/rate-limit depth. We absorb its best parts (HITL outcome, dry-run mode) into the WAF. |
| PS-8.1 Agent Budget Controller | Great ops story but commoditized (LiteLLM et al. already do this); weaker innovation signal. |

---

## 2. What the evaluators demand (from the problem statement doc)

- Production-ready, **deployed on AWS** (Lambda/ECS/EKS), governing agents also on AWS
  — scores higher than localhost.
- Handles **concurrent requests, persists state, exposes a usable API**.
- **Logging, error handling, health check.**
- Connects to **at least one real LLM provider** (not mocked).
- Extra points: deployment quality, integration breadth, plug-in-ability to a real
  enterprise AI stack without rework.

**Submission requirements (hard rules):**
- Zip file, publicly accessible URL, submitted via Google Form.
- **Strictly no public sharing** — no public GitHub, LinkedIn, social media.
- 5–8 min video: quick demo **at the start**, then how the solution works.
- PDF write-up: problem statement, technical solution, **architecture diagrams**,
  how it works, what it solves, **comparison to market solutions**.
- Code + clear README + **well-documented automated deployment scripts** so reviewers
  can independently verify claims.

**PS-5.1 success criteria (each becomes a named integration test + demo scene):**
1. Rate limit fires correctly after N calls within the window.
2. Parameter blocklist catches a simulated injection attempt in a tool parameter.
3. Out-of-scope data access is blocked.
4. Sequence rule enforcement blocks a tool called out of expected order.
5. Dashboard updates in real time as calls flow through.
6. **Bonus:** Shadow mode — log what would be blocked without blocking, for safe rule
   calibration before enforcement.

---

## 3. Architecture

```
                        ┌─────────────────────────── AWS ────────────────────────────┐
 User / Demo driver     │                                                            │
      │                 │   ┌──────────────┐  MCP (streamable HTTP)  ┌────────────┐  │
      ▼                 │   │ Sample Agents │ ──────────────────────► │  AGENT WAF │  │
 ┌──────────┐           │   │ (Claude Agent │                        │  (FastAPI   │  │
 │ Demo CLI │──────────►│   │  SDK, Lambda/ │ ◄──────────────────────│  on Lambda) │  │
 └──────────┘           │   │  container)   │   allow/block/HITL     └─────┬──────┘  │
                        │   └──────────────┘                               │         │
                        │        │ calls Claude API (Haiku 4.5)            │         │
                        │        ▼                                         ▼         │
                        │   Anthropic API              ┌──────────────────────────┐  │
                        │                              │ Rule Engine (YAML policy)│  │
                        │                              │ rate-limit │ params      │  │
                        │                              │ data-scope │ sequence    │  │
                        │                              │ shadow mode │ HITL queue │  │
                        │                              └─────┬────────────┬───────┘  │
                        │                                    ▼            ▼          │
                        │                              DynamoDB      Audit log       │
                        │                            (state, counters, (hash-chained,│
                        │                             sessions, queue)  OTel-shaped) │
                        │                                    │                       │
                        │                                    ▼                       │
                        │                        Live Dashboard (SSE/poll,           │
                        │                        served by same service)             │
                        └────────────────────────────────────────────────────────────┘
```

Request flow: **agent → WAF → rule pipeline → disposition (allow / block / HITL-hold /
shadow-log) → tool → response → audit record → dashboard.**

### Component decisions

| Component | Choice | Rationale |
|---|---|---|
| Proxy protocol | **MCP (streamable HTTP)** — the WAF *is* an MCP server fronting real downstream tools | MCP is the industry tool-layer standard (Anthropic, OpenAI, Google, Microsoft). Makes the WAF drop-in for any MCP-speaking agent → "plugs into a real enterprise stack without rework." |
| API framework | FastAPI + Pydantic | Industry default for AI services; typed request validation is itself part of the security story. OpenAPI docs auto-generated. |
| Policy format | Declarative **YAML policy-as-code**, versioned in repo, JSON-Schema-validated in CI | Governance-as-code (Unit 10 spirit) without building PS-10.1. Invalid policy blocks deploy. |
| Rule engine | Small, fully unit-tested custom evaluator: rate-limit, param blocklist/size, data-scope, sequence rules | Zero heavy dependencies, fully explainable decisions. OPA compatibility noted as roadmap. |
| State | **DynamoDB** — atomic counters (rate limits), session state, HITL queue, audit log | Always-free 25 GB; serverless; survives concurrent Lambdas → proves concurrency + persistence. |
| Compute | **AWS Lambda + API Gateway** (or function URLs), one-command **SAM/CDK** deploy | Always-free 1M req/month → $0. "Deployed on Lambda governing agents also on AWS" is verbatim their top scoring example. |
| Sample agents | 2–3 real agents on the **Claude Agent SDK** calling **Claude Haiku 4.5**: a support agent (mock-CRM tools), a data-analyst agent, one "compromised" agent for attack demos | Real LLM provider requirement; showcases the current Anthropic agent stack (agent loop, MCP client, sessions). |
| Observability | Structured JSON logs + spans shaped to **OpenTelemetry GenAI semantic conventions** (`gen_ai.*`), CloudWatch, `/health` + `/metrics` | OTel GenAI conventions are the emerging CNCF standard for LLM/agent tracing — cheap, deeply credible signal. |
| Dashboard | Single-page live dashboard (traffic, blocks, top rules fired, per-agent risk), served by the same service | Required by success criteria; demo gold. |

### Failure-mode policy (document explicitly — seniors love this)

- Rule-engine error on a **write/destructive** tool → **fail closed** (block + alert):
  protects the customer's data.
- Rule-engine error on a **read** tool → **fail open with alert**: protects uptime.
- Anthropic API calls: retries with exponential backoff; idempotency keys on tool
  forwarding; timeouts everywhere; dead-letter queue for unprocessable events.

---

## 4. Innovations (what lifts this above "did the assignment")

1. **Shadow mode** (the PS bonus): new rules run log-only first, then flip to enforce —
   exactly how AWS WAF ships rules. Demo: rule in shadow → "would-have-blocked" events
   on dashboard → flip → real blocks.
2. **HITL disposition** (borrowed from PS-3.1): fourth outcome beyond allow/block —
   high-risk calls pause in a DynamoDB review queue; human approves/rejects from the
   dashboard; the tool call resumes or fails. Graduated oversight (Unit 9) in miniature.
3. **Behavioral risk score — the data-science signature.** Per agent-session running
   anomaly score from tool-call frequency, sequence n-grams, and parameter
   distributions vs a recorded baseline. Repeated near-miss blocks escalate ("probing
   detection"). Baseline, drift, calibration, false-positive tradeoff — documented as
   proper DS methodology in the PDF.
4. **Hash-chained audit log**: each record embeds the previous record's hash →
   tamper-evident governance records. One afternoon of work, huge "audit-grade"
   credibility (EU AI Act hook).
5. **Policy-as-code + CI**: GitHub Actions validates policy YAML against schema;
   invalid policy fails the pipeline. `sam deploy` one-command deployment.
6. **Attack demo suite**: scripted scenarios mapping 1:1 to success criteria —
   prompt-injected agent attempting bulk-destructive ops, parameter smuggling,
   out-of-scope customer record access, tool-order abuse, runaway loop caught by rate
   limiting.

---

## 5. Coverage map — every requested concept

| Concept | Where it appears |
|---|---|
| Agentic AI / looping | Real Claude Agent SDK agents with the full agent loop |
| Memory | Session state in DynamoDB; behavioral baseline as cross-session memory; PDF paragraph on Anthropic memory-tool / context-editing design influence |
| MCP | The WAF speaks MCP on both sides — the industry's chosen governance surface |
| API & API usage | Documented REST/MCP API, auto-generated OpenAPI, queryable policy/audit endpoints |
| RAG | Honest scoping: core WAF doesn't need it. Optional stretch: embedding-similarity check of tool parameters against a small corpus of sensitive-data descriptors (PS-5.3's technique in miniature) — only if time permits |
| Monitoring | OTel-GenAI-shaped logs, CloudWatch, `/health`, `/metrics`, live dashboard |
| Error handling | Fail-open/fail-closed policy, retries/backoff, timeouts, idempotency, DLQ |
| Cloud / AWS | Lambda, API Gateway, DynamoDB, CloudWatch, SAM/CDK IaC — always-free tier |
| ML/DS in production | Anomaly scorer: baseline → calibration → thresholds → drift; dashboard analytics |
| Claude Code skills | Project `CLAUDE.md` + custom slash commands: `/attack-sim`, `/policy-check`, `/deploy` — described in the PDF's "how we built it" section |
| CI/CD | GitHub Actions (private repo): tests + policy validation + deploy gate |

---

## 6. Addressing Aivar's motto — customer needs in every decision

Named personas in the PDF, and a "customer impact" line on every design decision:

- **Persona 1 — Platform/Security Engineer:** needs drop-in enforcement with zero agent
  code changes → hence a *transparent MCP proxy*.
- **Persona 2 — Compliance Officer:** needs audit-grade, tamper-evident, human-readable
  records → hence hash-chained logs and plain-English block reasons.
- **Shadow mode = customer empathy:** enterprises can't break production agents to
  adopt governance; observe first, enforce second.
- **Fail-mode policy = customer-driven:** fail-closed on destructive ops protects their
  data; fail-open-with-alert on reads protects their uptime.
- **Explainable refusals:** every block returns a clear reason to the agent and the log
  — the customer's end-user deserves to know why.
- PDF closes with a **"Voice of the customer" table:** requirement → design decision →
  evidence in demo.

---

## 7. Winning over senior ex-AWS reviewers

1. **One-sentence narrative:** "There is a WAF for HTTP. There is nothing for agent
   tool calls. Agents are the new request traffic."
2. **Well-Architected Framework mapping** (security, reliability, cost optimization,
   operational excellence) — they have written hundreds of these reviews.
3. **Operational maturity over feature count:** health checks, runbook section,
   failure-mode table, load-test results (k6/locust: N concurrent agents, p95 latency
   of the proxy hop), cost model table ($0 idle / pennies under load).
4. **Comparison-to-market section** (explicitly required): Bedrock AgentCore Gateway
   (managed, AWS-locked vs ours: OSS-style, MCP-native, self-hostable), Citrix MCP
   Gateway, Microsoft Agent Governance Toolkit, MintMCP/Lasso-class gateways.
5. **Honest limitations section:** no semantic DLP, single-region, DynamoDB
   hot-partition risk at extreme scale, OTel GenAI conventions still in Development
   status. Bar-raisers distrust documents with no tradeoffs.

---

## 8. Cost plan

| Item | Cost |
|---|---|
| Lambda (always-free 1M req/mo) | $0 |
| API Gateway / function URLs | $0 at demo scale |
| DynamoDB (always-free 25 GB) | $0 |
| CloudWatch basic | $0 |
| Anthropic API (Haiku 4.5 demo traffic) | one-time ~$5 credit |
| Claude Code (development) | existing subscription |
| **Total recurring** | **≈ $0/month** |

Note: the Claude Code subscription covers development, not deployed API calls — the
~$5 API credit is the only real spend.

---

## 9. Deliverables plan (their submission spec, exceeded)

1. **PDF write-up (~12–15 pages):** problem & market context (EU AI Act Aug-2026,
   Gartner/McKinsey numbers) → personas → architecture (diagrams: system context,
   request-flow sequence, rule-pipeline flowchart, DynamoDB data model, deployment) →
   design decisions with customer-impact rationale → DS methodology for anomaly
   scoring → Well-Architected mapping → market comparison → limitations & roadmap.
   Diagrams in Mermaid / diagrams.net.
2. **Video (5–8 min):** 90-second demo montage FIRST (their instruction) — live
   dashboard during the attack suite, HITL approval, shadow→enforce flip — then
   architecture walkthrough, close on audit trail + cost.
3. **Repo (zipped, never public):** clean layout, README with 5-minute quickstart,
   `sam deploy` one-command script, seeded demo data, `.env.example`, unit tests for
   the rule engine + **integration tests named after each success criterion**, GitHub
   Actions CI config (private).

---

## 10. Build sequence (~5–7 days)

| Phase | Scope | Exit criterion |
|---|---|---|
| 1 | Rule engine + policy schema, unit-tested locally | All rule types pass unit tests |
| 2 | MCP proxy + mock CRM tools + audit log | End-to-end allow/block locally |
| 3 | Two Claude Agent SDK sample agents + attack suite | Attack scenarios reproduce criteria 1–4 |
| 4 | DynamoDB state + Lambda/SAM deployment | Criteria pass **in the deployed environment** |
| 5 | Dashboard + HITL queue + shadow mode + anomaly scorer | Criterion 5 + bonus pass deployed |
| 6 | Load test, hardening, docs, diagrams, video | Submission zip complete |

Each phase ends with the relevant success criterion passing in AWS, not just localhost.

---

## 11. Sources (research, 2026-07-12)

**MCP gateways & agent security market**
- Integrate.io — Best MCP Gateways & AI Agent Security Tools 2026: https://www.integrate.io/blog/best-mcp-gateways-and-ai-agent-security-tools/
- TrueFoundry — 10 Best MCP Gateways in 2026: https://www.truefoundry.com/blog/best-mcp-gateways
- Obot — 13 Best MCP Gateways for Enterprise 2026: https://obot.ai/blog/the-13-best-mcp-gateways-for-enterprise-teams/
- Help Net Security — Citrix MCP Gateway launch (Jul 9, 2026): https://www.helpnetsecurity.com/2026/07/09/citrix-mcp-gateway/
- MintMCP — MCP Security for Enterprises checklist: https://www.mintmcp.com/blog/mcp-security-enterprises
- Cequence — CIS MCP Security Guide: https://www.cequence.ai/blog/ai/cis-mcp-security-guide-how-to-govern-ai-agent-access-in-enterprise-environments/

**Runtime guardrails / action-layer governance**
- Galileo — Best AI Agent Guardrails 2026: https://galileo.ai/blog/best-ai-agent-guardrails-solutions
- APort — Pre-Action Authorization Compared 2026: https://aport.io/blog/best-ai-agent-guardrails-2026-pre-action-authorization-compared/
- Context Studios — AI Agent Security & Governance Tools 2026: https://www.contextstudios.ai/guides/ai-agent-security-governance-tools-2026
- Linx — Top Agentic AI Security Solutions 2026: https://www.linx.security/blog/top-agentic-ai-security-solutions

**AWS**
- AWS — AgentCore Policy + Bedrock Guardrails GA (Jun 2026): https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-bedrock-agentcore-policy-guardrails-generally-available/
- AWS docs — AgentCore Gateway: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html
- AWS blog — Introducing AgentCore Gateway: https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/

**Anthropic / agent engineering**
- Claude Agent SDK overview: https://code.claude.com/docs/en/agent-sdk/overview
- Anthropic — Equipping agents for the real world with Agent Skills: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Anthropic — Effective harnesses for long-running agents: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic — 2026 Agentic Coding Trends Report: https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf

**Observability**
- Uptrace — OpenTelemetry for AI Systems (2026): https://uptrace.dev/blog/opentelemetry-ai-systems
- Greptime — OTel GenAI semantic conventions, LLM/agent/MCP tracing: https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions
- Langfuse — OTel integration: https://langfuse.com/integrations/native/opentelemetry
- OpenObserve — OpenTelemetry for LLMs SRE guide 2026: https://openobserve.ai/blog/opentelemetry-for-llms/
