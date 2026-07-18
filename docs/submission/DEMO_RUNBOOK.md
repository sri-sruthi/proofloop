# ProofLoop PS-6.2 Local Demo Runbook

**Duration:** 6-8 minutes  
**Mode:** local-only, fake model, synthetic data  
**Status:** implemented and locally tested on Python 3.12.7; not deployed

## Safety preflight

Before recording:

- use only reserved synthetic invoice text;
- keep the API key in the shell and masked browser field; never narrate, print,
  paste into slides, or record it;
- do not run the Bedrock smoke script or any AWS/SAM deployment command;
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

## Timed narration

### 0:00-0:45 - customer problem

> Configuration dashboards can stay green after a runtime guardrail silently
> stops executing. ProofLoop answers PS-6.2 by binding each obligation to fresh,
> exact runtime evidence and making uncertainty visible as AMBER rather than
> treating missing data as success.

State the honest boundary: local vertical slice, deterministic fake model,
synthetic data, no AWS deployment and no real Bedrock call.

### 0:45-1:40 - architecture

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

### 1:40-2:30 - happy path

Run the Terminal 3 request. Point only to these safe response fields:

- `workflow_status: COMPLETED`;
- `disposition: ACCEPT_FOR_POLICY_EVALUATION` - explicitly not payment approval;
- `model_usage.model_calls: 1`;
- four `ACCEPTED` evidence receipts;
- `overall_compliance_status: GREEN`.

Explain that the fifth supporting evidence item is the independently scheduled,
model-free safe schema canary.

### 2:30-3:40 - dashboard

Open `http://localhost:8000`, enter the same local key in the password field,
and load the prefilled boundary. Point to:

- GREEN plus the freshness explanation;
- all four control cards;
- the operator-safe next action;
- reason and evidence references;
- the last-seven-days transition;
- the incident empty state.

Clear the saved key before leaving the page or capturing a screenshot.

### 3:40-5:15 - deterministic failures and recovery

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

For the assignment's SLA-focused foundation demo, optionally run:

```bash
python scripts/demo_proofloop.py
```

That deterministic scenario shows:

```text
GREEN -> AMBER -> RED -> AMBER -> GREEN
```

and a resolved incident. Do not describe either script as live AWS telemetry.

### 5:15-6:20 - evidence and engineering controls

Open `docs/submission/MANUAL_QA_EVIDENCE.md` and state:

- 266 tests passed under pytest 9.1.1;
- mypy, Ruff, Bandit, strict dependency audit, compileall, both demos, the
  template validator, source imports, dashboard syntax, privacy tests and
  isolation/secret scans passed;
- all 14 manual scenarios passed at their labeled boundaries;
- no raw invoice or prompt is persisted by the supported contracts.

### 6:20-7:15 - honest release verdict

Close with the current boundary:

- RUFF-01, BANDIT-01 and AUDIT-01 are closed by their authorized owners;
- the complete Python 3.12 local code gate passes with pytest 9.1.1;
- Python 3.13, SAM validation/build, GitHub CI, AWS deployment and real Bedrock
  were not executed;
- AWS account activation and Mumbai Lambda availability are product-owner
  attested facts, not deployment evidence from this run.

> The functional local slice is strong enough to demonstrate, but it is not a
> production-ready release. The local code blockers are closed; the next step
> is the separately authorized Python 3.13, SAM, CI and reviewed-change-set gate.

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
