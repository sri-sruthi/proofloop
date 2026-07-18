# Final Problem-Statement Decision — Market Research (Jul 16, 2026)

*Fresh, exhaustive web pass done Thu Jul 16 (build eve). Question asked of every candidate:
is it TOUGH, is it WHITESPACE (no real market solution), can Sri explain it cold, and can
it ship production-grade by Saturday night?*

## What the evaluators actually reward (from the PS doc itself)
Production readiness: deployed on AWS governing real AI workloads, concurrent requests,
persisted state, usable API, logging/error handling/health check, real LLM provider,
"pluggable into a real enterprise AI stack without significant rework."
**Nowhere is problem difficulty scored.** Toughness only matters if it's FINISHED.
The write-up explicitly requires a market comparison — so whitespace is scored, via that.

## Market reality per candidate (verified Jul 16)

### PS-5.1 The Agent WAF — ❌ most crowded square on the board
- **AWS AgentCore Policy went GA Mar 3, 2026**: Cedar policies evaluated on every MCP tool
  invocation at the AgentCore gateway, deterministic ALLOW/DENY, natural-language policy
  authoring, 13 regions. It IS an agent WAF, from the evaluators' own former employer.
- **Pipelock** — open-source AI agent firewall (May 2026). The free version of PS-5.1 exists.
- Venture/acquired platforms all in runtime agent security: **Zenity** (step-level runtime
  monitoring + guardrails), **Lasso** (behavioral intent, MCP visibility),
  **Prompt Security → SentinelOne**, **Lakera → Check Point**, **Aim → Cato**.
- Verdict: an ex-AWS panel reads a WAF submission against AgentCore Policy. The mandatory
  market-comparison section becomes "a weekend version of a thing AWS shipped in March."
  Liking it because "it's AWS-related" is backwards — EVERY option gets deployed on AWS;
  that box is checked regardless of PS.

### PS-8.1 Agent Budget Controller — ❌ crowded
- LiteLLM (per-key budgets, budget_duration, 429 on exhaustion), Portkey (virtual keys,
  per-team budgets, failover), TrueFoundry (MCP-aware cost governance), Kong AI Gateway.
  Budgets are a checkbox feature of every LLM gateway in 2026.

### PS-2.3 Delegation Chain Governor — ⚠️ whitespace but wrong shape
- Hottest identity topic of 2026: OAuth OBO/token-exchange for agents, WorkOS "multi-hop
  delegation problem," Strata, Scalekit, Arcade. **No delegation spec has reached RFC
  status (as of Apr 2026)** — genuine standards vacuum, so anything built is de-facto novel.
- But the core is signed tokens, scope attenuation, verification chains — cryptographic
  systems engineering. Zero data science. Sri would be defending JWT internals in an
  interview instead of her actual expertise. Pass, but mention it in the write-up's
  related-work section (it's adjacent to whatever we build).

### PS-4.3 Cross-Session Adversarial Pattern Detector — ✅ WHITESPACE, tough, and hers
- **Everything in this space is 2026 research, not product**: FragBench (cross-session
  attacks hidden in benign-looking fragments), "Cross-Session Threats in AI Agents:
  Benchmark, Evaluation, and Algorithms," latent/activation probing for multi-turn attacks,
  graph-based cross-session detectors hitting F1 0.88–0.96 in papers.
- Products (Zenity, Lasso) monitor **per-agent, per-step**. Fraud/abuse platforms (Sift,
  Arkose) score user sessions for classic abuse, NOT LLM-guardrail probing. Nobody ships
  per-USER, cross-SESSION correlation for LLM apps. Aivar's own PS context asserts this
  gap — and unlike PS-5.1's context (falsified by AgentCore), research CONFIRMS it here.
- Difficulty: real. Three distinct detectors + a decaying risk accumulator + calibration
  against a benign high-volume user (explicit false-positive criterion). This is the most
  algorithmically demanding non-crypto PS in the set.
- Fit: it is literally Sri's IoT-IDS work transplanted — behavioral baselines, anomaly
  scoring, threshold calibration, FPR control — on LLM session streams. Unit 4 is
  "Observability & Behavioral Monitoring," i.e., analytics, not attack-crafting. The
  "attacks" we must simulate are scripted traffic patterns (paraphrase variation,
  sequential enumeration), not jailbreak engineering.

### PS-5.3 Semantic Data Exfiltration Detector — ✅ runner-up
- Space is thin but ACTIVATING: Symantec + Google Agent Gateway DLP partnership, Harmonic,
  Strac doing GenAI DLP; paraphrase/reconstruction detection still mostly arXiv.
- DS-shaped (embeddings + LLM-judge cascade + calibration + eval suite with FPR<20%
  criterion), most contained scope of all — the safety pick if time collapses.

### Others considered and dropped
- PS-1.2 MCP Risk Scanner: MCP scanners exist (mcp-scan et al.); scanning/systems shaped.
- PS-8.2 Model Substitution Governance: genuine whitespace (GateScope paper measured silent
  substitutions across 10 commercial gateways; gateways treat it as routing, not
  governance) — but scope too small to read as "tough." Good write-up citation.
- PS-7.1 / 9.1 / 4.1: prior full plans exist (see respective PROJECT_PLAN docs). Still
  solid, but 7.1/9.1 are less "tough/whitespace" than 4.3, and 4.1's market is crowded.

## Decision matrix (1–5)

| | Whitespace | Toughness | Sri-fit (DS) | Finishable by Sat | Aivar-fit |
|---|---|---|---|---|---|
| PS-5.1 WAF | 1 | 3 | 2 | 4 | 3 (they know AgentCore does it) |
| PS-2.3 Delegation | 4 | 5 | 1 | 2 | 4 |
| **PS-4.3 Cross-session** | **5** | **4** | **5** | **4** | **5** |
| PS-5.3 Semantic exfil | 4 | 4 | 5 | 5 | 4 |
| PS-8.1 Budget | 1 | 2 | 3 | 5 | 3 |

## VERDICT
**Build PS-4.3 — Cross-Session Adversarial Pattern Detector** (working name: **Vigil**).
Runner-up / fallback if Thursday night goes badly: PS-5.3.
Full build spec: `PROJECT_PLAN_PS4.3_CrossSession_Vigil.md`.

### The Aivar pitch (write-up framing)
Aivar sells the "Governed Agentic AI Stack" (Velogent = agentic automation, Kubogent =
MLOps, all on Bedrock). Their guardrails, like everyone's, are per-request. Vigil is the
**SOC layer above the guardrail**: it assumes each guardrail decision is correct in
isolation and asks the question nobody's product asks — *is this USER, across days of
sessions, mapping our policy boundary?* It plugs into any Bedrock/AgentCore deployment as
an event consumer (integration breadth criterion), and the demo governs the #1 proven
production agent use case of 2026: a customer-support agent (Klarna-class deployments —
2/3 of support chats, ~$60M/yr saved — are exactly what enterprises run and exactly what
attackers probe).

## Sources
- AgentCore Policy GA + Cedar: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html · https://aws.amazon.com/blogs/security/why-policy-in-amazon-bedrock-agentcore-chose-cedar-for-securing-agentic-workflows/ · https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/
- Agent security market: https://www.linx.security/blog/top-agentic-ai-security-solutions · https://zenity.io/ · https://www.helpnetsecurity.com/2026/05/04/pipelock-open-source-ai-agent-firewall/ · https://www.paloaltonetworks.com/cyberpedia/agentic-ai-security-solutions
- Cross-session research (the whitespace evidence): https://arxiv.org/abs/2604.28129 (latent multi-turn detection) · https://arxiv.org/html/2604.21131 (Cross-Session Threats benchmark) · https://arxiv.org/pdf/2605.11029 (FragBench) · https://www.giskard.ai/knowledge/cross-session-leak-when-your-ai-assistant-becomes-a-data-breach
- Delegation/identity: https://workos.com/blog/oauth-multi-hop-delegation-ai-agents · https://www.strata.io/blog/agentic-identity/why-agentic-ai-demands-more-from-oauth-6a/ · https://arxiv.org/pdf/2603.24775 (AIP)
- Cost gateways: https://usagebox.com/articles/llm-gateway-cost-control-token-quotas-2026 · https://www.almtoolbox.com/blog/litellm-ai-gateway-cost-tracking-guardrails-budgets/
- Substitution governance gap: https://arxiv.org/html/2604.21083 (GateScope)
- Semantic exfil market: https://www.strac.io/blog/ai-dlp · https://www.security.com/feature-stories/symantec-dlp-google-agent-gateway-agentic-ai-security
- Agent adoption/use cases: https://ecorpit.com/enterprise-ai-agents-production-use-cases-2026/ · https://firstpagesage.com/reports/agentic-ai-adoption-statistics/
