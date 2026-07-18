# Decision Brief — Which Problem Statement to Build
*2026-07-12 · Read this first, then the two full plans.*

Two complete plans exist in this folder. Both target the same 2026 trend stack (MCP,
Claude Agent SDK, AWS free tier, OpenTelemetry, EU AI Act framing) and the same
deliverables. They differ in their **core** and therefore in how you hold up under
interview scrutiny.

| | **Option A — PS-5.1 Agent WAF** (`PROJECT_PLAN.md`) | **Option B — PS-3.2 Behavioral Detector** (`PROJECT_PLAN_PS3.2_BehavioralDetector.md`) |
|---|---|---|
| One-liner | "AWS WAF, but for agent tool calls" | "Detect prompt injection by what the agent *does*, not what the prompt *says*" |
| Core discipline | Systems engineering (proxy, rate-limit state, rule engine, HITL queue) | **Behavioral anomaly detection + calibration** (data science) |
| Matches your resume? | Partially — you *can* build it, but no resume project proves it | **Directly** — it's your IoT-IDS + LLM-eval + deepfake-calibration work retargeted |
| Pitch appeal to ex-AWS founders | **Very high** (WAF is an AWS flagship; instant recognition) | High (OWASP #1 LLM risk; "watch behavior not text" is a sharp hook) |
| Interview-defense strength | Medium — deepest questions hit systems areas you haven't shipped | **Very high** — deepest questions (threshold, FPR, drift) hit your published strengths |
| Personal narrative in the video | About the system | **About you** ("I showed IDS collapse F1 0.999→0.387; agents are the new traffic") |
| Demo drama | Strong (blocks, dashboard, shadow→enforce) | **Strong+** (poisoned tool hijacks agent → flagged in one turn → session suspended live) |
| RAG fit | Bolted-on stretch goal | **Native** (one injection poisons a retrieved doc) |
| Scrutiny risk | Higher (polished system > demonstrated skill = probing risk) | **Lower** (artifact and author aligned) |
| Cost | ~$0/mo + ~$5 API | ~$0/mo + ~$3–5 API |

## The core tradeoff
- **Option A** has the *better cold pitch* — a senior ex-AWS reviewer reads "Agent WAF"
  and immediately gets it.
- **Option B** has the *better defense and the better personal story* — because its hard
  core is the exact thing your resume already proves three times over, you get stronger
  the more they push, and your video tells a story about *you*, not about Claude Code.

## The "will they scrutinize AI-built work?" question
The doc explicitly permits any AI coding tools. What gets scrutinized is a **gap between
the artifact and the author** — a polished system whose builder can't defend its
decisions. Both plans are AI-assisted; the difference is that with Option B, every hard
decision (why this threshold, what's the false-positive story, how does it handle drift)
sits on ground you've already walked. That is the safest way to "stand out" without
risking the exact failure mode you're worried about.

## Recommendation
**Option B (PS-3.2).** Same trend coverage, same production polish, same ~$0 cost — but
its center of gravity is your proven specialty, which turns interview pressure from a
risk into an advantage. Keep Option A as the fallback if you decide the WAF framing is
worth more than the resume alignment.

*(You asked to keep both — done. Nothing here overwrites `PROJECT_PLAN.md`.)*

---

## UPDATE (2026-07-12) — a third input + verified company intel

A second AI (Codex) independently recommended **PS-5.1**, and its analysis prompted me
to verify facts about Aivar and the competition. See
`CODEX_AEGISGATE_AND_SYNTHESIS.md` for the full write-up. Key changes to the picture:

- **Aivar is deeply AWS/Bedrock** (four ex-AWS founders, AWS Advanced Tier Partner, built
  on Bedrock; tagline "Governed Agentic AI Stack"). Their accelerators **Velogent**
  (agentic automation) and **Kubogent** (ML Ops) show they value *both* governance
  engineering *and* production ML rigor.
- **AWS AgentCore Policy is GA (Mar 2026)** and already does PS-5.1's exact job (Cedar
  policy, tool-call interception, LOG_ONLY/enforce). The founders know it cold — so a
  straight PS-5.1 competes head-on with a product *they built the company on*.
- This makes **PS-3.2 more differentiated**, not less: AgentCore does deterministic
  policy + content guardrails, **not** behavioral/ML detection of successful injection.

**Revised recommendation — now three options, ranked for _this candidate_:**
1. **Synthesis** ("Sentinel-on-AegisGate"): Codex's bounded support-agent demo + a *thin*
   deterministic boundary + the behavioral detector as the signature. Best overall fit.
2. **Pure PS-3.2**: safest, most finishable, maximum resume alignment.
3. **Pure PS-5.1**: best abstract product & cold pitch, but highest scrutiny risk for you
   (competes with AgentCore on systems-engineering terrain your resume doesn't cover).

Whichever you pick, adopt Codex's production apparatus and the bounded support-agent
scenario (see `CODEX_AEGISGATE_AND_SYNTHESIS.md` §5 for the reusable list).
