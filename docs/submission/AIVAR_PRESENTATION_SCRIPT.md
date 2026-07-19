# Presentation Script — ProofLoop PS-6.2

**Target duration:** ~8 minutes. Screen directions (`SCREEN:`) are separated
from spoken narration (`SAY:`). Use only synthetic data; never show API keys,
account IDs, MFA information, login URLs, private role ARNs, real customer
invoices, prompts, or raw model output.

---

## 0:00–0:40 — Open with the demo, not a slide

**SCREEN:** Terminal. Run `python scripts/demo_proofloop.py`. Let the output
scroll: `GREEN -> AMBER -> RED -> AMBER -> GREEN`.

**SAY:** "So instead of a slide, let's just start with this running. What
you're watching is the whole lifecycle of ProofLoop in one go — evidence is
healthy, it goes GREEN; evidence gets stale, AMBER; something actually
fails, RED; and it only comes back to GREEN once there's real proof the fix
worked. None of that is a model deciding anything. It's just deterministic
rules, and that's kind of the whole point of this project."

## 0:40–1:35 — The problem

**SAY:** "Here's what got me thinking about this. AI agents are being given
more and more real authority now — reading documents, calling tools,
actually influencing decisions. And the safety controls around them, things
like PII redaction or a human-review step, usually get built once and then
nobody touches them again. But they break quietly. A redaction rule stops
matching after a format change, a validation step gets skipped in a
refactor, a review queue backs up and nobody notices for weeks. And this is
a Day 2 problem — it doesn't show up at launch, it shows up later, after
everyone's stopped watching closely. A normal config dashboard will happily
show green through all of that, because it's only reporting what was
*set up*, not what's actually happening right now. That's the gap I built
ProofLoop to close."

## 1:35–2:35 — The live, hosted system

**SCREEN:** Open `https://d1xanj4sg0mmpg.cloudfront.net`. Enter the demo API
key privately (off-screen or blurred), click **Load assurance record**.
Point to the GREEN badge, the four controls, the evidence references, and
the transition log.

**SAY:** "And this isn't a local demo — it's live right now. The dashboard's
on CloudFront, private S3 behind it, talking to a real backend: API
Gateway, Lambda, an actual Amazon Bedrock call. Every control you see here —
redaction, audit logging, the human-review boundary, the extraction
guardrail — is GREEN because there's fresh evidence for it, not because
someone flipped a switch. And look, here's the transition log — it actually
went from RED to GREEN earlier today, and you can see exactly what evidence
justified that."

## 2:35–3:30 — How it's built

**SCREEN:** Show the AWS deployment diagram.

**SAY:** "Quick walk through the pieces. API Gateway hits a Lambda function.
Before that Lambda ever talks to the model, it strips out email, phone,
account-like values — the model only ever sees redacted text. Bedrock does
the extraction, with structured output enforced at the API level, but
reconciliation and the human-review decision are plain deterministic code,
not the model. Evidence lands in DynamoDB. There's a second Lambda that
runs every five minutes on its own schedule to keep reconciling — and that
one has zero permission to call Bedrock, so the always-on loop literally
can't generate model cost. Ten CloudWatch alarms, two dead-letter queues,
nothing fails without someone finding out."

## 3:30–4:10 — A real scenario, start to finish

**SCREEN:** Optional — show a synthetic invoice snippet or the extracted
JSON output alongside the diagram, if you have it handy.

**SAY:** "Let me make that concrete with an actual case. Say an invoice
comes in — vendor's Acme Supplies, invoice INV-9, two line items, totaling
$105. That text hits redaction first. Then Bedrock pulls out the structured
fields: vendor, amount, line items. Separately, deterministic code checks
that against the purchase order on file — same vendor, same amount, so it
reconciles and gets accepted for the next step. If something didn't match,
or confidence was low, it would go to a human instead of just sliding
through. That's not hypothetical, by the way — it's the exact invoice I
used for the real Bedrock call this whole demo is built on."

## 4:10–5:00 — Deterministic verdict, real Bedrock call

**SCREEN:** Show the AI/assurance data-flow diagram.

**SAY:** "The model's job in all of that was narrow — read untrusted text,
output a strict schema, nothing else. It never grades its own work. A
separate deterministic function decides GREEN, AMBER, or RED. To be upfront
about what that invoice example actually proves: connectivity and contract
compatibility. It's not an accuracy claim — accuracy at scale needs a real
eval set, which I'll get to."

## 5:00–5:45 — AMBER, RED, and why recovery is strict

**SCREEN:** Show the state/remediation diagram.

**SAY:** "AMBER just means uncertain — evidence missing or stale. RED means
something concrete actually failed. And recovery's deliberately strict: if
you re-enable a broken control, status goes to AMBER, not straight back to
GREEN. You need fresh passing evidence, observed *after* the fix, before it
trusts you again. Because a fix can be wrong, or stale, or just never
actually deployed — so the system assumes that until it sees otherwise."

## 5:45–6:30 — Security, reliability, cost

**SAY:** "A few things worth calling out plainly. The API key here is a
development boundary, not production auth — I'm not pretending otherwise.
Only the API Lambda can call Bedrock, and only on one exact model ARN; the
scheduler can't touch it at all. Nothing raw — no invoice text, no prompt,
no model output — ever gets logged or stored. Both async paths have
dead-letter queues with bounded retries, so failures get captured instead
of silently dropped. And cost-wise, it's all pay-per-use serverless, hard
caps on model calls and tokens — the only real fixed cost is about a dollar
a month in alarms."

## 6:30–7:10 — Where data science fits, and where it doesn't

**SCREEN:** Show the control/data/evaluation-planes diagram.

**SAY:** "There's also a separate offline layer for measuring extraction
quality — match rate, calibration, cost tradeoffs. It's completely walled
off from the runtime — can't write into the verdict, and it's not even
packaged into the deployed Lambda. Right now the results are on synthetic
data only, so I'm not making any production accuracy claim — that
discipline's the point. Confidence scores can inform a human decision about
thresholds. They don't get to declare anything GREEN themselves."

## 7:10–7:40 — Why this, and not just existing monitoring

**SAY:** "Config dashboards and general observability can tell you a
service is up. They don't bind one proof to one requirement, and they
don't refuse to show green without current evidence. That's the whole
contribution here — a small, deterministic layer for the one failure mode
that's otherwise invisible: a control that's configured right but has
quietly stopped working. It complements existing monitoring, not replaces
it."

## 7:40–8:00 — Limitations and close

**SAY:** "To be honest about where this stands — it's a controlled
development deployment, not enterprise production. One shared API key, not
per-user identity. The business tools are in-memory fixtures, not a real
ERP. No load testing, no multi-region. The evaluation layer makes no
production accuracy claim, full stop — that's written down, not hidden.
What is real: a live, hosted system with an actual model call, a
five-minute assurance loop that's been running for hours, and a verdict
you can go check yourself, right now, at the link on screen."

---

## Screen-direction summary (quick reference)

| Time | Screen |
|---|---|
| 0:00 | Terminal — `python scripts/demo_proofloop.py` |
| 1:35 | Browser — `https://d1xanj4sg0mmpg.cloudfront.net`, load record, show GREEN + transition log |
| 2:35 | AWS deployment diagram |
| 3:30 | (optional) synthetic invoice / extracted JSON snippet |
| 4:10 | AI/assurance data-flow diagram |
| 5:00 | State/remediation diagram |
| 6:30 | Control/data/evaluation-planes diagram |
| 7:40 | Back to the live dashboard URL for the close |

**Do not show on screen at any point:** the API key value, AWS account ID,
MFA device details, IAM role ARNs, login URLs, or any raw invoice/prompt/model
response text.
