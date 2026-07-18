# Final Agent ⇄ Domain Contract Compatibility Review

**Reviewer:** Claude Code (agent-layer owner)
**Date:** 2026-07-18
**Scope:** Confirm the agent result contracts and guardrail control observations
can later map to requirement-bound `EvidenceEnvelope` objects under the corrected,
frozen domain contracts (Codex `DOMAIN_FOUNDATION_CORRECTIONS.md`, findings
B1/H1–H9). Read-only against `src/proofloop/domain/models.py`. The agent package
imports nothing from `proofloop.domain` and constructs no evidence object.

## Verdict

**NO BLOCKING INCOMPATIBILITY.** The corrected domain contracts and the agent
result contracts are structurally compatible. Every field a requirement-bound
`EvidenceEnvelope` needs is either (a) carried by the agent layer today, or
(b) intentionally a composition-root concern (customer/deployment context and
version-vector labels), exactly as Codex's migration instructions specify.

No finding is raised for the sake of appearing thorough. The items below are a
mapping plan and two **non-blocking** recommendations, not defects.

## What the agent layer now carries (integration-ready surface)

- `InvoiceWorkflowResult` — `document_id`, `status`, `final_stage`,
  `disposition`, `started_at`/`completed_at` (UTC-aware), `prompt_binding`
  (`prompt_id`, `version`, SHA-256 `content_hash`), `model_stats`
  (`provider_id`, `model_calls`, `input_tokens`, `output_tokens`), `tool_calls`
  (per-tool `ToolInvocationOutcome`), `control_observations`, `reasons`,
  `human_review_ticket_id`, typed `extraction_failure`/`reconciliation_failure`,
  `safe_next_action`.
- `ControlObservation` — stable `control_key`, `ControlOutcome`
  (PASS/FAIL/UNAVAILABLE), UTC `observed_at`, `component`, `guardrail_version`,
  `reason`, `safe_next_action`, PII-free scalar `attributes`.

## Field-by-field mapping to `EvidenceEnvelope`

| Domain field (corrected) | Source in agent layer | Notes |
|---|---|---|
| `evidence_id` | composition root | synthesize, unique per emitted event |
| `control_id` | mapping from `control_key`/stage | e.g. `guardrail.pii_redaction` → its control |
| **`requirement_id`** (B1) | one per `control_key` / per disposition control | distinct id per observation → **one event never proves two requirements** |
| `evidence_type` | fixed per control | `CONTROL_EXECUTION`/`CONTROL_OUTCOME`/`AUDIT_EVENT` |
| `source` | `component` / agent name | e.g. `proofloop.agents.guardrails` |
| `source_event_id` | `f"{document_id}:{control_key}:{started_at}"` | deterministic, unique within scope |
| `workflow` (`WorkflowExecutionReference`) | composition root supplies `tenant_id`, **`environment`** (H5), **`assurance_boundary_id`** (H5), `workflow_id`, `execution_id`, `trace_id` | correctly NOT derived from the agent layer |
| `outcome` (`EvidenceOutcome`) | `ControlOutcome` / `disposition` | PASS→PASS, FAIL→FAIL, UNAVAILABLE→UNAVAILABLE (subset of domain enum; all map) |
| `observed_at` | `ControlObservation.observed_at` / workflow timestamps | UTC-aware, preserved raw (H7) |
| `ingested_at` | composition root (ingest time) | evaluator applies skew policy |
| `provenance` (`Provenance`, H6) | see next table | agent supplies applicable version dims |
| `attributes` (`tuple[EvidenceAttribute,…]`) | `ControlAttribute` (scalar) | scalar, unique keys, **no raw PII** |

### Provenance (H6) ten-field vector

| Provenance field | Mandatory? | Agent-layer source |
|---|---|---|
| `component_version` | yes | composition-root label for the agent component |
| `policy_version` | yes | composition-root label for `PolicyConfig` version |
| `schema_version` | yes | composition-root label for the contract schema |
| `orchestration_version` | yes | composition-root label for `run_invoice_workflow` |
| `runtime_config_version` | yes | composition-root label for runtime config |
| `prompt_version` | None if N/A | `prompt_binding.version` (+ `content_hash` for pinning) |
| `model_version` | None if N/A | `model_stats.provider_id` / `BedrockProviderConfig.model_id` |
| `tool_catalog_version` | None if N/A | label for `APPROVED_TOOL_SPECS` |
| `mcp_server_version` | None if N/A | `None` this phase (no MCP runtime) |
| `guardrail_version` | None if N/A | `ControlObservation.guardrail_version` |

Deterministic evidence (e.g. the deterministic policy/HITL control) keeps the
five mandatory versions and sets genuinely inapplicable prompt/model/tool/MCP/
guardrail fields to `None` — matching the corrected `Provenance` semantics.

## Consistency with the frozen invariants

- **B1 (requirement binding):** each observation has a distinct `control_key`;
  the emitter stamps a distinct `requirement_id` and `source_event_id` per event.
  Nothing in the agent layer relabels one event across requirements.
- **H1/PASS-only:** `ControlOutcome.PASS` is the only outcome that should map to
  a GREEN-supporting `EvidenceOutcome.PASS`; FAIL→RED, UNAVAILABLE→AMBER.
- **H2:** the agent layer never constructs `AssuranceEvaluation`/
  `StateTransitionExplanation`; a future explanation layer consumes immutable
  structured truth and only polishes prose.
- **H5:** `environment` and `assurance_boundary_id` are supplied by the
  composition root, never derived from an AWS ARN/account/region in the agent core.
- **H7:** agent timestamps are raw UTC and never normalized; the evaluator owns
  skew tolerance.

## Non-blocking recommendations (for the composition root, not the agent layer)

1. **Deterministic `source_event_id` scheme.** Adopt
   `f"{document_id}:{control_key}:{started_at.isoformat()}"` so re-emission is
   idempotent and duplicate-scoped correctly. (The agent result already carries
   all three inputs; no agent change required.)
2. **Optional `run_id`/correlation id.** Not added to the agent result to
   preserve deterministic replay (a UUID would break byte-for-byte replay).
   The composition root can derive `execution_id`/`trace_id` from
   `document_id` + `started_at`, or inject a correlation id at that layer.

## Conclusion

Integration is unblocked from the agent side. When Codex confirms the
`control_key → requirement_id` and `disposition → control` mapping table against
the frozen contracts, the evidence-emission adapter (Codex/shared) can be written
without any change to the agent business logic. Emission itself remains out of
scope until that cross-review, per the ownership boundary.
