# Presentation Script — ProofLoop PS-6.2

**Target duration:** ~8 minutes. Screen directions (`SCREEN:`) are separated
from spoken narration (`SAY:`). Use only synthetic data; never show API keys,
account IDs, MFA information, login URLs, private role ARNs, real customer
invoices, prompts, or raw model output.

---

## 0:00–0:40 — Open with the working demo, not a slide

**SCREEN:** Terminal. Run `python scripts/demo_proofloop.py`. Let the output
scroll: `GREEN -> AMBER -> RED -> AMBER -> GREEN`.

**SAY:** "ProofLoop asks a stronger question than 'is a safety control
configured?' It asks whether the control actually ran, produced the right
outcome, and has fresh evidence for this exact customer boundary — right
now. What you just saw is the whole lifecycle in one run: healthy evidence
gives GREEN; evidence going stale gives AMBER; a confirmed failure gives
RED; and only fresh proof after a real fix brings it back to GREEN. Every
one of those transitions is a deterministic rule, not a model's opinion."

## 0:40–1:30 — The problem

**SCREEN:** Stay on terminal or a blank slide.

**SAY:** "AI agents are increasingly given real authority — reading
documents, calling tools, influencing decisions. The safety controls around
them — PII redaction, output validation, a human-review boundary — are
usually built once and then trusted forever. In practice they silently
regress: a redaction rule stops matching, a validation step gets bypassed
in a refactor, a review queue fills up unnoticed. This is a Day 2 problem,
not a Day 1 problem — it doesn't show up when a system launches, it shows
up weeks or months later, quietly, after everyone has stopped watching the
build. A normal configuration dashboard still shows green through all of
that, because it only reports what was *configured*, never what is
*currently happening*. That gap is what ProofLoop closes."

## 1:30–2:40 — Live hosted system, not just local code

**SCREEN:** Open `https://d1xanj4sg0mmpg.cloudfront.net` in a browser. Enter
the demo API key privately (off-screen or blurred), click **Load assurance
record**. Point to the GREEN badge, the four controls, the evidence
references, and the seven-day transition log.

**SAY:** "This is not a local demo — it's live in AWS right now. The
dashboard is hosted on CloudFront in front of a private S3 bucket; HTTPS
only, no public bucket access. It's talking to a real backend: API Gateway,
a Lambda function, and a real Amazon Bedrock model call. Every control here
— PII redaction, audit logging, the human-review boundary, the extraction
schema guardrail — is GREEN because it has fresh, correlated, passing
evidence, not because someone flipped a switch. And here's the transition
log: you can see it actually went from RED to GREEN earlier today, with the
exact evidence that justified it."

## 2:40–3:40 — Architecture and why each piece is there

**SCREEN:** Show the AWS deployment diagram (`diagrams/2_aws_deployment.png`).

**SAY:** "Under the hood: API Gateway routes to an API Lambda. Before that
Lambda ever calls the model, it redacts email, phone, and account-like
values from the invoice text — the model only ever sees redacted data.
Bedrock's Converse API, with native structured-output schema enforcement,
does the extraction; deterministic code — not the model — does
reconciliation, policy, and the human-review decision. Evidence lands in
DynamoDB. A second, separate Lambda runs on a five-minute EventBridge
schedule to keep reconciling — and critically, that scheduled function has
no permission to call Bedrock at all, so the continuous-assurance loop can
never generate model cost. Ten CloudWatch alarms and two dead-letter queues
mean nothing fails silently."

## 3:40–4:40 — Deterministic assurance and real Bedrock proof

**SCREEN:** Show the AI/assurance data-flow diagram
(`diagrams/3_ai_assurance_data_flow.png`).

**SAY:** "The model only ever reads untrusted text into a strict schema — it
never grades itself. A deterministic evaluator, a pure function with no
model call, decides GREEN, AMBER, or RED. We proved this live: an
authenticated request triggered a real Bedrock Converse call, using
Mistral's Ministral model, with structured JSON output enforced by the API
itself. That's a real model invocation, real tokens, a real DynamoDB write
— not a stub. And to be precise about what that proves: it proves
connectivity and contract compatibility. It is not a claim about model
accuracy at scale — that would need a proper evaluation dataset, which I'll
come back to."

## 4:40–5:30 — AMBER, RED, and why recovery is strict

**SCREEN:** Show the state/remediation diagram (`diagrams/4_state_remediation_flow.png`).

**SAY:** "AMBER means uncertainty — evidence is missing, stale, or
ambiguous. ProofLoop never invents a RED from silence. RED means a current,
unambiguous failure signal was actually observed. And recovery is
deliberately stricter than flipping a switch: if you re-enable a broken
control, status moves only to AMBER — 'remediation unverified' — never
straight back to GREEN. Only fresh, correlated PASS evidence, observed
*after* the fix, restores GREEN on the next sync. A repaired control can be
wrong, stale, or never actually deployed — this rule assumes that until
proven otherwise."

## 5:30–6:20 — Security, reliability, and cost discipline

**SAY:** "Security: the API key here is an explicit development
authentication boundary, not production identity — that's stated plainly,
not hidden. Only the API Lambda's role can call Bedrock, and only on one
exact model ARN; the scheduled Lambda has zero Bedrock permission,
structurally enforced and tested. No raw invoice text, prompt, or model
output is ever logged or stored — evidence is bounded metadata only.
Reliability: both the schedule path and the async Lambda path have
dedicated dead-letter queues with bounded retries, so a failure is captured,
never dropped. Cost: everything is pay-per-use serverless — no idle
servers, a hard cap on model calls and output tokens per request, and the
only material fixed cost is about a dollar a month in CloudWatch alarms."

## 6:20–7:00 — Where data science fits, and where it deliberately does not

**SCREEN:** Show the control/data/evaluation-planes diagram
(`diagrams/5_control_data_evaluation_planes.png`).

**SAY:** "There's a separate, offline evaluation layer for measuring
extraction quality — match rate, calibration, cost trade-offs — against a
labeled dataset. It's structurally isolated: it cannot write into the
runtime verdict, enforced by automated import checks in both directions,
and it's excluded from the deployed Lambda package entirely. Today's
results are on synthetic fixtures, so no production accuracy claim is made
anywhere — that discipline is the point. Confidence and calibration inform
a human decision about thresholds; they never get to declare GREEN
themselves."

## 7:00–7:40 — How this differs from what teams already have

**SAY:** "Configuration dashboards and general observability tools can tell
you a service is running, but they don't bind one proof to one requirement
with exact provenance, and they don't refuse to show green without current
evidence. That's ProofLoop's whole contribution: a small, deterministic,
auditable assurance layer purpose-built for the failure mode that's
otherwise invisible — an AI control that's configured correctly but has
quietly stopped working. This is a complement to existing monitoring and
GRC tooling, not a claim to replace it."

## 7:40–8:00 — Honest limitations and close

**SAY:** "To be direct about what this is not: this is a controlled
development deployment, not enterprise production. Authentication is a
single shared key, not per-user identity. Business tools — purchase order
and vendor lookups — are in-memory fixtures, not a real ERP integration.
There's no load testing, no multi-region failover, and the evaluation layer
makes no production accuracy claim. Every one of those limits is written
down in the submission, not hidden. What is real: a live, hosted,
end-to-end deployment with a real model call, a continuous five-minute
assurance loop that's been running for hours, and a deterministic verdict
you can independently verify right now at the URL on screen."

---

## Screen-direction summary (quick reference)

| Time | Screen |
|---|---|
| 0:00 | Terminal — `python scripts/demo_proofloop.py` |
| 1:30 | Browser — `https://d1xanj4sg0mmpg.cloudfront.net`, load record, show GREEN + transition log |
| 2:40 | `diagrams/2_aws_deployment.png` |
| 3:40 | `diagrams/3_ai_assurance_data_flow.png` |
| 4:40 | `diagrams/4_state_remediation_flow.png` |
| 6:20 | `diagrams/5_control_data_evaluation_planes.png` |
| 7:40 | Back to the live dashboard URL for the close |

**Do not show on screen at any point:** the API key value, AWS account ID,
MFA device details, IAM role ARNs, login URLs, or any raw invoice/prompt/model
response text.
