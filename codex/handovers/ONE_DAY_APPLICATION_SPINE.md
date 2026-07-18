# ProofLoop Track B — local-to-AWS application spine handoff

Task:
Build the PS-6.2 local-to-AWS vertical slice requested in the Track B brief,
without modifying Claude-owned agent paths and without committing, pushing,
deploying, or creating cloud resources.

Customer outcome:
A reviewer can run one deterministic invoice-control demo in seconds, observe
`GREEN -> AMBER -> RED -> AMBER -> GREEN`, query an explicit compliance record,
timeline, and incidents through an authenticated local API, inspect the same
state in a static dashboard, and review a budget-conscious AWS SAM package.
GREEN requires current correlated PASS proof; quiet telemetry is AMBER, and RED
requires explicit current failure evidence.

Files read:
- Track B brief:
  `/Users/srisruthi/.codex/attachments/6bf7c172-af3d-47dd-8e92-d155ae779285/pasted-text.txt`
- Original assignment source:
  `/Users/srisruthi/Downloads/Problem_Statements_Aivar.docx` (PS-6.2 extracted
  and checked against the four acceptance criteria)
- `docs/PROJECT_RULES.md`
- `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`
- `codex/handovers/DOMAIN_FOUNDATION_CORRECTIONS.md`
- `claude/handovers/AGENT_FOUNDATION_HANDOFF.md`
- Current domain and agent source/tests, plus all Track B implementation/tests.

Files changed:
- `src/proofloop/application/**`
- `src/proofloop/api/**`
- `src/proofloop/infrastructure/**`
- `tests/application/**`
- `tests/api/**`
- `tests/integration/**`
- `scripts/demo_proofloop.py`
- `dashboard/**`
- `infra/**`
- `.github/workflows/ci.yml`
- `README.md`
- `.env.example`
- `pyproject.toml`
- `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md`
- `codex/handovers/ONE_DAY_APPLICATION_SPINE.md`

No file under `src/proofloop/agents/**`, `tests/agents/**`, or `claude/**` was
modified by Track B.

Review findings resolved:
- The PS-6.2 flags are tri-state, so missing/stale/ambiguous proof cannot be
  misrepresented as either `true` or an explicit failure.
- Silence never manufactures RED; the 48-hour demo records one safe synthetic
  canary FAIL with a supporting evidence ID.
- Re-enabling configuration only sets a strict verification boundary and
  remains AMBER until fresh post-remediation PASS evidence arrives.
- Application isolation is AST-tested after moving demo orchestration out of
  the application layer and into infrastructure.
- SAM functions explicitly use the custom makefile builder required by the
  repository's `src/` layout; a regression test protects this.
- Dashboard defaults and field mappings were aligned to the seeded local API
  identity and actual control IDs.
- The handbook's historical foundation failures are labeled as a superseded
  snapshot instead of contradicting the current Track B result.
- Independent review reproduced four blockers, all now regression-covered:
  conflicting reuse is retained as quarantine evidence and forces AMBER;
  allowlisted attributes are strict booleans and evidence references are bounded
  opaque values; canary evidence requires `synthetic=true` and
  `side_effects_absent=true`; and stale syncs cannot overwrite newer state
  because current compliance, transition and incidents commit atomically with an
  optimistic comparison.
- Full workflow/execution/trace identity and a unique evidence-reference index
  make in-memory and DynamoDB idempotency behavior consistent.
- Service-clock ingestion stamps prevent callers from extending/shortening TTL.
- Malformed base64 and invalid/oversized WSGI lengths return bounded structured
  errors; OpenAPI now contains usable Pydantic-backed schemas and parameters.
- RED SLA creation and AMBER-to-RED incident escalation are tested in place.
- Scheduled partial failure raises after all scopes, with bounded EventBridge and
  Lambda retry planes, SQS failure destinations and secret-free logs.
- `AgentRegistryIndex` replaces full-table discovery scans; CI performs a target
  runtime SAM build and verifies both handlers load from their artifacts.
- Virtual time cannot move backwards, remediation time is UTC-validated, the
  dashboard renders each API control's own state, and demo output names evidence.
- A final independent re-review found same-timestamp DynamoDB transitions could
  sort by hash rather than commit order. The adapter now advances a per-agent
  monotonic revision in the same optimistic transaction and uses it as the
  timeline sort sequence. The exact `AMBER -> RED -> AMBER` same-clock path,
  `latest_transition`, and subsequent AMBER SLA incident are regression-tested.
- Independent final verdict: **accepted for local integration**, with no
  remaining Critical or Important finding in the reviewed Track B scope.

Contract changes:
- Added immutable application contracts: `AgentScope`, `AgentDefinition`,
  `ComplianceReadModel`, `ControlCompliance`, `TimelineEntry`,
  `ComplianceIncident`, ingestion results, SLA policy, and sync outcome.
- Added repository ports for agents, evidence, compliance, timeline, and
  incidents plus `AssuranceStateRepository.commit_state`; no AWS SDK types enter
  domain/application contracts.
- Added the six required API routes plus authenticated schema-complete OpenAPI,
  stable error envelopes, request/trace IDs, pre-read/decode size validation,
  and configured-origin CORS.
- Added one-table DynamoDB keys scoped by tenant, environment, assurance
  boundary, full workflow identity and agent-prefixed records, with server-time
  TTL, transactional idempotency/evidence-ID indexes, optimistic aggregate
  commits, monotonic timeline revision, and a query-only registry GSI.

Migration instructions for Claude:
1. Keep existing agent ownership paths unchanged.
2. Emit `EvidenceEnvelope` values to `POST /v1/evidence` with the registered
   agent ID and exact tenant/environment/boundary/workflow/provenance tuple.
3. Bind each event to one declared `control_id` and `requirement_id`; never reuse
   one event to prove multiple obligations.
4. Send only bounded opaque evidence/source references and allowlisted boolean
   control metadata. Do not include invoice text, prompt/tool payloads, free-text
   attributes, or PII. The service owns `ingested_at` regardless of caller input.
5. Treat a duplicate source event as successful idempotent delivery; treat
   `EVIDENCE_CONFLICT` as quarantine/investigation, not a retry loop. Its next
   sync is deliberately AMBER until the ambiguity is resolved by a new source ID.
6. Do not infer RED from quiet telemetry. If a canary is used, it must be the
   single reserved NO_OP/SANDBOX probe with confirmed absent side effects.
7. After a repair/configuration change, emit a fresh PASS strictly after the
   remediation boundary before expecting GREEN.

Tests added:
- Application ingestion: accepted, duplicate, conflict, declaration, boundary,
  provenance, strict boolean metadata, PII-shaped references, safe-canary
  attestation, server-time stamping, and post-conflict AMBER behavior.
- Sync/read model: exact PS-6.2 fields, GREEN/AMBER/RED semantics, and
  remediation recovery.
- Timeline/incidents: append-only status changes, seven-day range, repeat-sync
  deduplication, AMBER/RED SLA, in-place escalation, deterministic create-once,
  and evidence-backed resolution.
- API: auth, schema-complete OpenAPI, vertical route path, CORS, safe
  validation/conflict/base64/body-length errors, tenant isolation, and time ranges.
- Integration: in-memory composition; DynamoDB full-workflow keys, unique
  references, quarantine, TTL, atomic stale-write rejection and exact same-clock
  transition/SLA ordering; Lambda/scheduled retries and DLQs; registry GSI;
  built-artifact verification; dashboard/demo; SAM contract; and all four named
  PS-6.2 assignment criteria.
- Isolation: application cannot import infrastructure; domain/application/API
  cannot import AWS SDKs.

Commands executed:
```text
python --version
python -m pytest -q
python -m mypy src/proofloop tests
python scripts/demo_proofloop.py
python -m compileall -q src tests scripts infra/scripts
env PYTHONPATH=src python -c "import the HTTP/scheduled Lambda entry points"
python infra/scripts/validate_template.py
node --check dashboard/app.js
rg source scans for AWS imports and dangerous Python patterns
python -m pip check
```

Actual results:
- Python: `3.12.7`; Node: `v22.18.0`.
- Full pytest: `224 passed in 1.00s`.
- Full mypy: `Success: no issues found in 79 source files`.
- Demo: exact `GREEN -> AMBER -> RED -> AMBER -> GREEN`; one resolved incident
  contains four resolution evidence IDs.
- Compile, source-tree Lambda entry-point imports, structural SAM validation,
  YAML parsing, both Lambda make dry-runs, and dashboard JavaScript syntax: exit 0.
- Source scans: no AWS imports in domain/application/API and no matches for the
  selected dangerous Python execution patterns.
- A real localhost WSGI smoke earlier in this Track B run returned HTTP 200 for
  health, authenticated sync, and authenticated GREEN compliance with four
  controls/four evidence references.
- `sam`, Ruff, Bandit, pip-audit, Python 3.13, and `uv` are unavailable locally;
  they were not represented as executed.
- The machine-wide `pip check` failed on unrelated pre-existing Anaconda
  package conflicts. This checkout was not installed into a clean isolated
  environment, so there is no clean local dependency-audit claim. The clean CI
  workflow is defined but has not run.

Production risks checked:
- No unsupported GREEN, no silence-derived RED, no premature recovery.
- Conflict quarantine, safe-canary attestations, boolean-only metadata, bounded
  opaque references, and server-owned ingestion time.
- Exact tenant/environment/boundary/workflow and declaration validation.
- Idempotency collision behavior and customer-safe errors.
- No raw invoice/PII attributes; log messages contain operational metadata only.
- Constant-time API-key comparison, bounded request body, configured-origin CORS.
- Tenant-scoped/full-workflow DynamoDB keys, TTLs, transactional idempotency,
  monotonic-revision aggregate state and same-clock timeline ordering, GSI
  registry queries, encrypted/on-demand table, bounded concurrency/retries, SQS
  failure destinations, and 30-day log retention.
- SAM contains no NAT Gateway, OpenSearch, EKS, ECS, or always-on compute.
- No AWS/LLM dependency in domain/application contracts.

Known limitations:
- Not deployed and not production-ready. No cloud resource was created.
- API-key authentication is a demonstration boundary, not full identity,
  authorization, rotation, throttling, quotas, WAF, or per-role policy.
- DynamoDB transactions were contract-tested with a deterministic fake, not a
  live table; aggregate revision/order and stale-write rejection are covered,
  while real throttling, cancellation, concurrency and eventual GSI visibility
  need target-environment tests.
- Local WSGI is not a production server; the dashboard is read-only and not
  deployed.
- EventBridge/Lambda, CloudWatch delivery/alarms, rollback, load, fault injection,
  and live external telemetry emitters remain unverified in AWS.
- Per-agent reconciliation reads the retained eight-day evidence prefix; quotas,
  backpressure, scale limits and a possible workflow/time index remain open.
- DLQ alarms, replay ownership, and a verified replay runbook remain open.
- Local Python 3.13, SAM CLI, Ruff, Bandit, and pip-audit verification is absent;
  the CI workflow has not run.
- The shared host Python environment has unrelated dependency conflicts and no
  project lockfile because `uv` is unavailable.

Human decisions still required:
- Authorize or reject a first non-production AWS deployment (`DEPLOY`) after CI
  passes; select AWS account, region, stack name, allowed browser origin, and
  API-key secret delivery/rotation method.
- Choose production identity/authorization (for example, an external gateway or
  IAM-backed design) and incident SLA values.
- Define per-agent ingestion quotas/backpressure and the volume threshold for a
  workflow/time-oriented evidence index beyond the current eight-day prefix.
- Define DLQ alarm thresholds, replay ownership, and a safe replay/runbook policy.
- Choose monitoring/alarms, operational ownership, retention requirements, and
  cost budget before production use.

Five files the human should inspect:
1. `src/proofloop/application/service.py`
2. `src/proofloop/application/models.py`
3. `src/proofloop/infrastructure/dynamodb.py`
4. `src/proofloop/api/app.py`
5. `infra/template.yaml`

Concepts the human must understand:
- GREEN is a proof claim; AMBER is uncertainty; RED needs explicit current FAIL.
- PS-6.2 booleans are tri-state and reason/evidence references are authoritative.
- Identity includes tenant, environment, assurance boundary, agent, workflow,
  execution, and trace; cross-boundary proof is never reusable.
- Idempotency includes workflow/execution/trace/source/source-event plus a unique
  evidence reference; contradictory reuse is quarantined and forces AMBER.
- A sync is an optimistic atomic state turn: stale GREEN cannot replace newer
  RED or split the compliance/timeline/incident ledger.
- Repair declarations do not prove control execution; fresh post-repair PASS does.
- The domain/application are cloud-neutral; infrastructure owns DynamoDB/Lambda.
- A package and CI definition are not deployment evidence.

Recommended Claude review focus:
- Confirm agent emitters can populate exact requirement binding and provenance
  without sending customer payloads or crossing the ownership boundary.
- Stress the integration with duplicate/out-of-order events, emitter retries,
  multi-tenant scopes, and post-remediation timestamps.
- Review whether current incident semantics and scheduled registry discovery fit
  the real customer/operator workflow before production hardening.
- Treat Track B APIs/contracts as integration inputs; do not weaken domain
  invariants to make an emitter easier to connect.

Documentation updated:
- Root `README.md` with local demo/API/dashboard/SAM commands and limitations.
- `.env.example` contains placeholders only.
- `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md` now contains Track B architecture,
  analogies, data flow, code map, decisions, acceptance mapping, demo narration,
  interview answers, fresh evidence, and production risks.
- `infra/README.md` documents build/deploy/delete commands and the data model.

Git diff summary:
The repository still has no baseline commit; `git status --short` reports the
working tree as untracked rather than a reviewable base/head diff. No Git
mutation was authorized or performed: no add, commit, branch change, push, PR,
or deployment.
