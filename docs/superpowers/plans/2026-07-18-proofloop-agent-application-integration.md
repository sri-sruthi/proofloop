# ProofLoop Track C Implementation Plan

> Approved for immediate execution on 2026-07-18. Follow TDD. Do not edit
> `src/proofloop/agents/**`, `tests/agents/**`, or `claude/**`. Do not commit,
> push, deploy, invoke AWS, or create paid resources.

**Goal:** Connect the corrected invoice workflow to ProofLoop's assurance spine
through a privacy-bounded infrastructure bridge and authenticated API route.

**Architecture:** The API receives an invoice-run protocol. Infrastructure
implements it by running the injected agent workflow, mapping observations to
requirement-bound evidence, ingesting and syncing through `ProofLoopService`,
and returning a bounded response. Provider and AWS SDK construction stay in the
composition root.

## Task 1: Freeze neutral API contracts and route behavior

**Files:**
- Create `src/proofloop/api/invoice_runs.py`
- Modify `src/proofloop/api/app.py`
- Create/modify `tests/api/test_invoice_runs.py`

1. Write failing tests for authentication, request/body bounds, absent runner,
   response privacy, OpenAPI schemas, and stable failure codes.
2. Add immutable bounded request/response models and an `InvoiceRunPort`.
3. Inject the port into `ProofLoopApi` and dispatch the invoice-run route.
4. Run the focused API tests and full existing API suite.

## Task 2: Define exact integrated controls and evidence mapping

**Files:**
- Create `src/proofloop/infrastructure/agent_integration.py`
- Create `tests/integration/test_agent_evidence_bridge.py`

1. Write failing tests for the four exact observation mappings, distinct
   requirement IDs/source events, raw UTC, exact workflow identity, all
   provenance fields, outcome mapping, runtime/schema-vs-canary separation,
   and approved boolean-only metadata.
2. Implement integration settings and the dedicated registered agent definition.
3. Implement deterministic bounded evidence/source identifiers.
4. Implement one-observation-to-one-envelope translation without forwarding
   reasons, counts, free text, or payloads.
5. Run focused mapping tests and isolation scans.

## Task 3: Run the workflow, ingest evidence, and synchronize assurance

**Files:**
- Modify `src/proofloop/infrastructure/agent_integration.py`
- Modify `tests/integration/test_agent_evidence_bridge.py`

1. Write failing end-to-end tests for agent-to-GREEN, exact replay idempotency,
   contradictory replay quarantine, malformed model output, model failure, tool
   failure, duplicate/HITL, call/token caps, safe canary RED, remediation AMBER,
   and post-remediation fresh GREEN.
2. Implement transient request conversion, dependency factories, workflow run,
   safe mapping/ingestion, synchronization, and bounded response construction.
3. Emit/seed the independently attested safe-canary PASS needed for the normal
   integrated baseline; never synthesize it from a runtime observation.
4. Run focused integration and application suites.

## Task 4: Wire local and Lambda composition, including Bedrock

**Files:**
- Modify `src/proofloop/infrastructure/composition.py`
- Modify `src/proofloop/infrastructure/lambda_handler.py` only if parity needs a
  bounded adapter correction
- Create/modify `tests/integration/test_agent_composition.py`
- Modify `tests/integration/test_lambda_handler.py`
- Modify `.env.example`

1. Write failing tests proving local/API/Lambda parity, FakeModelProvider local
   default, Bedrock stub-client injection, environment limit parsing, and boto3
   isolation.
2. Add provider/tool factories and shared application composition.
3. Construct boto3 only for explicitly selected Bedrock mode.
4. Add placeholder-only environment documentation.
5. Run composition/Lambda tests and import-isolation scans.

## Task 5: Add scoped SAM configuration and guarded smoke command

**Files:**
- Modify `infra/template.yaml`
- Modify `infra/scripts/validate_template.py`
- Modify `tests/integration/test_infrastructure_contract.py`
- Create `scripts/smoke_bedrock_invoice.py`
- Modify `infra/README.md`

1. Write failing structural tests for required model ID/ARN/region/limit
   parameters, exact `bedrock:InvokeModel` action/resource, and forbidden
   wildcard/always-on resources.
2. Add SAM parameters, environment variables, and least-privilege permission.
3. Add a smoke script that exits unless explicitly authorized by an environment
   guard and never logs request content.
4. Run structural validation and source Lambda imports; do not invoke AWS.

## Task 6: Build the integrated demonstration

**Files:**
- Create `scripts/demo_agent_to_compliance.py`
- Create/modify `tests/integration/test_agent_demo.py`

1. Write a failing output/behavior test for every required scene.
2. Implement the deterministic poisoned-invoice through recovery demonstration.
3. Ensure output contains only safe references, enum outcomes, counts for model
   usage (not PII findings), and no payment capability.
4. Run both deterministic demos.

## Task 7: Cross-layer privacy and adversarial regression gate

**Files:**
- Create `tests/integration/test_agent_privacy_boundary.py`
- Modify relevant integration/API tests only where necessary

1. Inspect provider request, emitted envelope, repository records, API/Lambda
   serialization, dashboard-bound compliance payload, and captured logs for all
   poisoned raw values and prohibited content.
2. Assert prompt injection remains only in the redacted untrusted provider
   channel and never becomes authority.
3. Assert only allowlisted booleans persist and no observation reason/count is
   forwarded.
4. Run the focused privacy tests, then the full suite.

## Task 8: Consolidate documentation and handoff

**Files:**
- Modify `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`
- Modify `README.md`
- Create `codex/handovers/FINAL_AGENT_APPLICATION_INTEGRATION.md`

1. Merge the corrected agent narrative and Track C architecture/status.
2. Document analogies, decisions, customer impact, code map, cost/privacy,
   production limitations, interview answers, and demo narration.
3. Record actual verification output only; keep deployment/real-provider claims
   explicitly false until executed.

## Task 9: Fresh completion verification

Run and record:

1. `python -m pytest -q`
2. `python -m mypy src/proofloop tests`
3. `python -m compileall -q src tests scripts infra/scripts`
4. `python scripts/demo_proofloop.py`
5. `python scripts/demo_agent_to_compliance.py`
6. `python infra/scripts/validate_template.py`
7. source-tree HTTP/scheduled Lambda import checks
8. `node --check dashboard/app.js`
9. AWS SDK/import-isolation, privacy, and dangerous-pattern scans
10. Available lint/security/dependency tools, with unavailable tools reported
    honestly.

Self-review the changed files and final diff. Finish with either
`READY_FOR_DEPLOY` or `BLOCKED_FOR_DEPLOY`, actual evidence, exact blockers, and
one explicit question for deployment authorization. Do not deploy.
