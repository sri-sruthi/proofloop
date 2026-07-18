# One-Week Plan — Three Priorities, Two Tracks
*Sun 2026-07-12 (late) → Mornings = internship (blocked). Evenings + nights = free.
Tuesday night = OFF/rest.*

## Deadline: CONFIRMED Sunday Jul 19 (exact time unknown)
Aivar confirmed the deadline is Sunday. Since TCS occupies Sun 8am–~11:15am, **plan to
submit Aivar SATURDAY NIGHT.** One quick win worth a 2-min check: find the *exact* Sunday
time. If it's Sunday evening (not morning), you gain Sunday afternoon (post-TCS, ~12pm+)
as a buffer for final polish. But build the plan around a Saturday-night submission so
you're never dependent on that buffer.

## Confirmed hard facts
- **Wed Jul 15 test = HARD ELIGIBILITY GATE** for all campus placements. Immovable #1.
  Fail = locked out of the season. Content: aptitude/verbal/reasoning/coding.
- **Sun Jul 19, 8am = TCS Priority NQT**, 190 min (≈ to ~11:15am). Sunday morning is
  100% TCS. Content = aptitude + Advanced Coding (NOT an ML knowledge test). PG bands:
  Prime ₹11.59 / Digital ₹7.39 / Ninja ₹3.62 LPA; coding drives the higher band.
  → **Aivar's real deadline is therefore SATURDAY NIGHT** (no Sunday buffer).
- The Wed gate and TCS share ONE prep track (aptitude/coding). Prep once, use twice.

## NOT this week (park for after)
- **Google ML Crash Course / ML-in-production**: helps neither test (both are aptitude/
  coding) and isn't needed for PS-3.2 (applied behavioral analytics = your IoT-IDS work,
  not DL theory). Great AFTER-crunch goal; scheduling it now would sabotage the 3 urgent
  things. Your ML/DL "weakness" is theory — a multi-week fix, not a this-week cram.

## The competing commitments
1. **Wed Jul 15 — CPET placement ELIGIBILITY GATE (confirmed hard gate).** 3 parts:
   Aptitude & Logical Reasoning + Verbal + **Technical** (CS/IT/AI/DS: DSA, Python, SQL,
   cloud, OS/networks, AI/ML/GenAI, system design, etc.). Prioritize to clear the cutoff,
   don't master it. Detailed tiered plan in CPET_GATE_PREP.md. Non-negotiable #1.
2. **Aivar project** — due Sun Jul 19, 9am. The dream (real industry AI). Scoped sprint.
3. **Sun Jul 19 — TCS placement test** (same skill set as #1). Backup job.

## The reframe that makes this doable: 2 tracks, not 3
- **Track A — Placement prep** (aptitude/reasoning/verbal/coding): serves BOTH the Wed
  eligibility test and the Sun TCS test. Front-load before Wed, then maintain.
- **Track B — Aivar**: build (Claude Code / Codex do most of it) + learn-to-explain +
  video. Sprint from Wed night → Sat.

## Priority logic
- **Floor = the tests** (esp. Wed if it's an eligibility gate — that's the only
  potentially irreversible outcome this week). If anything truly collides, tests win.
- **Aivar rewards "good + deeply understood," not "maximal."** A focused, well-explained
  project beats a sprawling or broken one. Your differentiator is EXPLAINING it.
- **TCS is mostly free** — the Wed prep already covers it. Submit Aivar 9am, then TCS.

## Day-by-day

| Day | Evening + Night |
|---|---|
| **Sun (tonight, late)** | Sleep. Just enroll in courses (5 min). Rest before Mon internship. |
| **Mon** | Gate Tier 1: aptitude + reasoning (Feel Free to Learn) + SQL/DSA brush-up. FIRST: get CPET pattern/cutoffs from T&P cell. (See CPET_GATE_PREP.md; also your TCS base.) |
| **Tue** | Eve: Gate Tier 2 verbal (CareerRide) + Tier 3 strengths (AI/ML, Python recall). **Night OFF — rest.** |
| **Wed** | Take eligibility test. Night: **Aivar begins** — skim compressed AWS+MCP essentials; Claude Code scaffolds repo. |
| **Thu** | Aivar core (Claude Code builds detector; you study concepts) + 30 min coding (TCS). |
| **Fri** | Aivar deploy + dashboard. **Checkpoint:** if AWS is fighting you → deploy on **Render or Railway (you already know these)** instead. Any cloud beats localhost. + 30 min aptitude. |
| **Sat** | Aivar finalize AND SUBMIT tonight (video, PDF, zip). Then light TCS review + sleep — TCS is 8am. |
| **Sun 8am** | TCS (190 min, until ~11:15am). Aivar already submitted Saturday night. |

## Aivar scope for THIS timeline (only ~3.5 evenings/nights: Wed–Sat)
- **Build pure PS-3.2 (behavioral injection detector)** — its DS core is already yours,
  so nearly all new learning is just AWS + MCP. Do NOT attempt the full synthesis.
- **Compress courses hard** (you no longer have ~24h): target ~4–6h AWS essentials
  (IAM, Lambda, DynamoDB, S3, CloudWatch — skip VPC/HA labs) + ~2–3h MCP basics. Learn
  the rest by reading what Claude Code builds. Drop the Claude Code course this week.
- **Claude Code / Codex do the building; you do the understanding.** Your scarce human
  hours go into being able to defend every design choice on camera.
- **Demo-first:** get one path working (agent → poisoned tool → detector flags → session
  suspended → dashboard) before adding scenarios.

## Decision rules
1. Tests are the floor; if a real collision happens, tests win.
2. Friday-night checkpoint: AWS fighting you → deploy on Render/Railway (you've done both
   before). AWS is REWARDED, not REQUIRED — no problem statement mandates it ("or
   equivalent" is in the rubric). Any cloud deploy + a real LLM provider beats localhost.
3. Never sacrifice the ability to EXPLAIN for one more feature.

## The "can I explain it?" checklist (rehearse Sat night, out loud)
- Why detect injection by behavior, not prompt text? (OWASP LLM01; classifiers miss
  *successful* injections)
- How did you set the threshold? What's your false-positive story? (your calibration work)
- How does it generalize / handle drift? (your IoT-IDS domain-adaptation story)
- Why Lambda + DynamoDB + S3? What does IAM protect? (from AWS essentials)
- What is MCP and why is it the right boundary? (from MCP basics)
- How is this different from AWS AgentCore? (AgentCore = deterministic Cedar policy +
  content guardrails; yours = behavioral/ML detection it doesn't do)

## Open question to resolve (tell Claude, and the plan adjusts)
- Is the **Wed test a hard eligibility gate** for all campus placements? (If yes → it is
  the immovable top priority.)
- **What time is the TCS test on Sunday?** (Confirms the 9am-submit-then-test sequence.)
