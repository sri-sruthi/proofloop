# ProofLoop PS-6.2 Local Demo Runbook

**Duration:** 6-8 minutes  
**Mode:** local-only, fake model, synthetic data  
**Status:** local Python 3.13, private Python 3.12/3.13 CI, SAM gates, and a
controlled-development AWS smoke pass. The deployed API completed one real
Bedrock-backed GREEN workflow with synthetic non-customer data.

## 30-45 second working demo - show this first

Start the recording with working behavior, not setup or slides. From the
repository root in the already prepared disposable environment, run:

```bash
python scripts/demo_proofloop.py
```

Keep the terminal framed on the five states:

```text
GREEN -> AMBER -> RED -> AMBER -> GREEN
```

Use this compact narration while the command runs:

> ProofLoop begins GREEN only with fresh, correlated PASS evidence. Advancing
> the synthetic clock makes that evidence stale, so it moves to AMBER. A safe
> no-side-effect canary provides explicit FAIL evidence and drives RED. Merely
> re-enabling configuration remains AMBER; only fresh post-remediation proof
> restores GREEN. The transition history and incident are recorded without a
> cloud account, customer data, or a model call.

This is a deterministic local working demo, not AWS telemetry. Separately, the
deployed API Gateway/Lambda/Bedrock/DynamoDB path was observed with synthetic
non-customer data and resulted in GREEN. Continue into the fuller
architecture/API/dashboard narrative below.

## Safety preflight

Before recording:

- use only reserved synthetic invoice text;
- keep the API key in the shell and masked browser field; never narrate, print,
  paste into slides, or record it;
- do not run an AWS deployment command during recording; do not reveal a private
  endpoint, API key, account identifier, customer payload or model output;
- do not show request bodies, prompts, model output, raw/redacted invoice text,
  tool payloads, environment dumps, or hidden reasoning;
- keep `docs/submission/MANUAL_QA_EVIDENCE.md` available for exact test counts
  and blockers.

## Terminal setup

Use a disposable environment; do not install globally:

```bash
python -m venv /tmp/proofloop-demo-venv
source /tmp/proofloop-demo-venv/bin/activate
python -m pip install -e ".[dev]"
export PROOFLOOP_API_KEY="choose-a-new-local-session-key"
export PROOFLOOP_MODEL_PROVIDER="fake"
```

Open three terminals from `/Users/srisruthi/Aivar Project`.

**Terminal 1 - API**

```bash
source /tmp/proofloop-demo-venv/bin/activate
export PROOFLOOP_API_KEY="the-same-local-session-key"
export PROOFLOOP_MODEL_PROVIDER="fake"
python -m proofloop.api.server
```

**Terminal 2 - dashboard**

```bash
python -m http.server 8000 --directory dashboard
```

**Terminal 3 - synthetic run**

```bash
source /tmp/proofloop-demo-venv/bin/activate
curl -sS -X POST \
  "http://127.0.0.1:8080/v1/agents/invoice-agent/runs/invoice?tenant_id=proofloop-demo&environment=LOCAL&assurance_boundary_id=proofloop-demo-local-invoices" \
  -H "X-API-Key: $PROOFLOOP_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"document_id":"synthetic-local-1","content_type":"TEXT_PLAIN","source_system":"local-demo","received_at":"2026-07-18T09:00:00Z","invoice_content":"Synthetic Acme Supplies invoice INV-9 for PO-1, total 105 USD."}'
```

The response should report `COMPLETED`, four accepted runtime receipts, one
bounded fake-model call, and overall `GREEN`. Do not expand or display fields
that contain transient request material; the safe response contract does not
return invoice content.

## Timed full narration

### 0:00-0:45 - working proof first

Run the 30-45 second demonstration above and show the complete state sequence.

### 0:45-1:20 - customer problem

> Configuration dashboards can stay green after a runtime guardrail silently
> stops executing. ProofLoop answers PS-6.2 by binding each obligation to fresh,
> exact runtime evidence and making uncertainty visible as AMBER rather than
> treating missing data as success.

State the honest boundary: local vertical slice, deterministic fake model,
synthetic data. The recorded local sequence is distinct from the separately
observed deployed Bedrock smoke; do not present local output as live telemetry.

### 1:20-2:05 - architecture

Show the architecture diagram in
`docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.md`.

Narrate the two cooperating responsibilities:

1. The invoice agent transiently redacts and extracts, reconciles with bounded
   deterministic tools, blocks duplicates for human review, and emits typed
   metadata-only observations.
2. The ProofLoop assurance service validates identity, correlation, provenance,
   collision and freshness; derives GREEN/AMBER/RED; then persists only the
   read model, transition timeline and incident records.

Emphasize that an LLM cannot set compliance status or next safe action.

### 2:05-2:55 - happy path

Run the Terminal 3 request. Point only to these safe response fields:

- `workflow_status: COMPLETED`;
- `disposition: ACCEPT_FOR_POLICY_EVALUATION` - explicitly not payment approval;
- `model_usage.model_calls: 1`;
- four `ACCEPTED` evidence receipts;
- `overall_compliance_status: GREEN`.

Explain that the fifth supporting evidence item is the independently scheduled,
model-free safe schema canary.

### 2:55-3:55 - dashboard

Open `http://localhost:8000`, enter the same local key in the password field,
and load the prefilled boundary. Point to:

- GREEN plus the freshness explanation;
- all four control cards;
- the operator-safe next action;
- reason and evidence references;
- the last-seven-days transition;
- the incident empty state.

Clear the saved key before leaving the page or capturing a screenshot.

For the controlled-development deployment evidence, use the separately saved
sanitized capture at
`docs/submission/evidence/proofloop_dashboard_deployed_green.png`. It was
loaded from the deployed backend, while its endpoint and API key are not shown.

### 3:55-5:20 - deterministic failures and recovery

Run:

```bash
python scripts/demo_agent_to_compliance.py
```

Narrate the summarized states only:

- poisoned input is redacted and handled as untrusted;
- a confirmed duplicate is `BLOCK` plus HITL, with no payment tool;
- exact fixed-clock evidence replay returns duplicate receipts;
- contradictory evidence produces conflict plus AMBER;
- a failing safe canary drives RED;
- remediation declaration alone produces AMBER;
- fresh runtime and canary evidence restore GREEN;
- malformed output and tool timeout fail safely.

The expected recovery sequence is:

```text
GREEN -> RED -> AMBER -> GREEN
```

The SLA-focused foundation demo already shown at the start produced
`GREEN -> AMBER -> RED -> AMBER -> GREEN` and a resolved incident. Do not
describe either script as live AWS telemetry.

### 5:20-6:20 - evidence and engineering controls

Open `docs/submission/MANUAL_QA_EVIDENCE.md` and state:

- 414 tests passed under pytest 9.1.1;
- mypy, Ruff, Bandit, strict dependency audit, compileall, both demos, the
  template validator, source imports, dashboard syntax, privacy tests and
  isolation/secret scans passed;
- all 14 manual scenarios passed at their labeled boundaries;
- no raw invoice or prompt is persisted by the supported contracts.

### 6:20-7:20 - honest release verdict

Close with the current boundary:

- RUFF-01, BANDIT-01 and AUDIT-01 are closed by their authorized owners;
- the clean local Python 3.13 gate passes with pytest 9.1.1 and 414 tests;
- private GitHub Actions passes on Python 3.12 and native ARM64 Python 3.13;
- local and CI SAM validation/build and both built-handler imports pass;
- the allowed-origin injection, schedule activation, and essential alarm
  findings remain accepted pre-change-set infrastructure blockers;
- AWS identity/model preflight, a CloudFormation change set, deployment, smoke,
  full alarm-notification delivery, rollback exercise and production-scale
  validation remain unexecuted;
- AWS account activation and Mumbai Lambda availability are product-owner
  attested facts, not deployment evidence from this run.

> The functional local slice is strong enough to demonstrate, but it is not a
> production-ready release. Python 3.13, SAM, and private CI are complete. The
> next step is the separately approved, test-driven infrastructure-hardening
> track; only after it passes CI may a read-only AWS preflight and non-executed
> change set be considered.

## Fast recovery during recording

| Symptom | Safe recovery |
|---|---|
| Dashboard says not connected | Confirm both local servers are running; confirm identity fields match the curl URL; re-enter the local key without showing it |
| Compliance returns not found | Run the synthetic invoice once, then reload the dashboard |
| Port already in use | Stop only the known demo process using that terminal; do not kill broad process groups |
| Browser shows stale state | Reload after the API run, re-enter the key, then load the record |
| Demo script differs from expected states | Stop the recording, capture the output, and treat it as a defect; do not improvise or edit implementation |

## Recording closeout

1. Click **Clear saved key**.
2. Stop the local API and static server with `Ctrl-C` in their own terminals.
3. Deactivate and optionally remove only the explicit disposable environment.
4. Confirm no AWS/Bedrock/deploy/Git action occurred.
