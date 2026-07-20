# PS-6.2 Requirement Traceability

Maps every assignment requirement to the exact code, test, or live evidence
that satisfies it.

| Requirement | Implementation | Test / evidence |
|---|---|---|
| Compliance schema (`guardrails_active`, `last_violation_timestamp`, `pii_redaction_enabled`, `audit_logging_enabled`, `hitl_configured`, `overall_compliance_status`) | `src/proofloop/application/models.py` (`ComplianceReadModel`) | `tests/application/`; live: `GET /v1/agents/{id}/compliance` |
| Runtime telemetry collector | `src/proofloop/agents/agent_integration.py`, `src/proofloop/infrastructure/agent_integration.py` | `tests/integration/test_agent_evidence_bridge.py`; live invoice run |
| Evidence / webhook API | `src/proofloop/api/app.py` (`POST /v1/evidence`) | `tests/api/test_api.py` |
| Five-minute sync (EventBridge + scheduled Lambda) | `infra/template.yaml` (`ProofLoopScheduledFunctionFiveMinuteReconciliation`), `src/proofloop/infrastructure/scheduled_handler.py` | `tests/integration/test_scheduled_hardening.py`; live: EventBridge rule `ENABLED`, dozens of consecutive successful cycles observed in CloudWatch |
| 24-hour AMBER on quiet evidence | `src/proofloop/domain/evaluator.py` freshness policy | `tests/domain/` freshness tests; local virtual-clock demo |
| 48-hour RED on confirmed failure | Reserved synthetic extraction-schema canary | `src/proofloop/infrastructure/agent_integration.py` (`run_safe_extraction_canary`) |
| Seven-day compliance timeline | `TimelineEntry`, `GET /v1/agents/{id}/timeline` | `tests/application/`; live timeline log with real `RED → GREEN` transition |
| SC1 — healthy controls → GREEN | Deterministic evaluator | Live: all four controls GREEN on hosted dashboard |
| SC2 — simulated failure → AMBER by 24h, RED by 48h | Virtual-clock test suite | `tests/integration/test_ps62_acceptance.py` |
| SC3 — correct timeline transitions | Append-only timeline | `tests/application/`; live transition log |
| SC4 — re-enable + fresh evidence → GREEN at next sync | `verification_required_after` boundary | `tests/integration/test_ps62_acceptance.py` |
| Bonus — configurable AMBER/RED SLA | `IncidentSlaPolicy` | `tests/application/` |
| Bonus — automatic incident + remediation ownership | Deterministic incident lifecycle | `tests/application/`, `GET /v1/agents/{id}/incidents` |
| Hosted, publicly reachable demo | `infra/web-template.yaml`, `infra/scripts/deploy_dashboard.sh` | Live: `https://d1xanj4sg0mmpg.cloudfront.net` |
| Real system integration (real model call) | `src/proofloop/agents/providers/bedrock.py` (Converse + structured output) | Live: authenticated invoice run, `model_calls ≥ 1`, real Bedrock response |
| Dashboard / report | `dashboard/` (static client) | Live browser proof, `docs/submission/evidence/proofloop_dashboard_live_browser_proof.png` |
