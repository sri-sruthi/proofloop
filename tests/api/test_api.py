from __future__ import annotations

import json
from datetime import timedelta

from .conftest import ingest_all_passes, make_evidence
from proofloop.api.app import ProofLoopApi
from proofloop.domain.models import EvidenceOutcome


API_KEY = "test-api-key"


def request(api: ProofLoopApi, method: str, path: str, *, body=None, key=API_KEY, headers=None):
    selected_headers = {"X-API-Key": key} if key is not None else {}
    selected_headers.update(headers or {})
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    route, separator, query_string = path.partition("?")
    return api.handle(
        method=method,
        path=route,
        query_string=query_string if separator else "",
        headers=selected_headers,
        body=payload,
    )


def query_for(agent) -> str:
    return (
        f"tenant_id={agent.scope.tenant_id}"
        f"&environment={agent.scope.environment.value}"
        f"&assurance_boundary_id={agent.scope.assurance_boundary_id}"
    )


def test_health_is_public_and_carries_request_trace_ids(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY)

    response = request(
        api,
        "GET",
        "/healthz",
        key=None,
        headers={"X-Request-ID": "request-123", "X-Trace-ID": "trace-123"},
    )

    assert response.status_code == 200
    assert response.json_body == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "request-123"
    assert response.headers["X-Trace-ID"] == "trace-123"


def test_non_health_endpoints_require_the_configured_api_key(system) -> None:
    service, _, _, agent = system
    api = ProofLoopApi(service=service, api_key=API_KEY)

    missing = request(
        api,
        "POST",
        f"/v1/agents/{agent.scope.agent_id}/sync?{query_for(agent)}",
        key=None,
    )
    wrong = request(
        api,
        "POST",
        f"/v1/agents/{agent.scope.agent_id}/sync?{query_for(agent)}",
        key="wrong",
    )

    assert missing.status_code == 401
    assert missing.json_body["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert wrong.status_code == 403
    assert wrong.json_body["error"]["code"] == "AUTHENTICATION_FAILED"


def test_local_dashboard_preflight_is_allowed_without_exposing_credentials(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(
        service=service,
        api_key=API_KEY,
        allowed_origin="http://localhost:8000",
    )

    response = api.handle(
        method="OPTIONS",
        path="/v1/evidence",
        query_string="",
        headers={"Origin": "http://localhost:8000"},
        body=b"",
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8000"
    assert response.headers["Access-Control-Allow-Headers"] == "X-API-Key, Content-Type, X-Request-ID, X-Trace-ID"
    assert "test-api-key" not in response.body.decode("utf-8")


def test_openapi_is_generated_from_all_required_routes(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY)

    response = request(api, "GET", "/openapi.json")

    assert response.status_code == 200
    assert set(response.json_body["paths"]) >= {
        "/healthz",
        "/v1/evidence",
        "/v1/agents/{agent_id}/sync",
        "/v1/agents/{agent_id}/compliance",
        "/v1/agents/{agent_id}/timeline",
        "/v1/agents/{agent_id}/incidents",
    }
    assert response.json_body["components"]["securitySchemes"]["ApiKeyAuth"]


def test_evidence_sync_and_read_endpoints_form_a_vertical_slice(system) -> None:
    service, _, _, agent = system
    api = ProofLoopApi(service=service, api_key=API_KEY)
    for control in agent.controls:
        event = make_evidence(agent, control.control_id)
        response = request(
            api,
            "POST",
            "/v1/evidence",
            body={"agent_id": agent.scope.agent_id, "evidence": event.model_dump(mode="json")},
        )
        assert response.status_code == 202
        assert response.json_body["status"] == "ACCEPTED"

    synced = request(
        api,
        "POST",
        f"/v1/agents/{agent.scope.agent_id}/sync?{query_for(agent)}",
    )
    compliance = request(
        api,
        "GET",
        f"/v1/agents/{agent.scope.agent_id}/compliance?{query_for(agent)}",
    )
    timeline = request(
        api,
        "GET",
        f"/v1/agents/{agent.scope.agent_id}/timeline?{query_for(agent)}",
    )
    incidents = request(
        api,
        "GET",
        f"/v1/agents/{agent.scope.agent_id}/incidents?{query_for(agent)}",
    )

    assert synced.status_code == 200
    assert compliance.json_body["overall_compliance_status"] == "GREEN"
    assert compliance.json_body["guardrails_active"] is True
    assert len(compliance.json_body["controls"]) == 4
    assert timeline.json_body["items"][0]["current_status"] == "GREEN"
    assert incidents.json_body == {"items": []}


def test_duplicate_and_conflict_have_stable_safe_responses(system) -> None:
    service, _, _, agent = system
    api = ProofLoopApi(service=service, api_key=API_KEY)
    event = make_evidence(
        agent,
        "pii-redaction",
        evidence_id="first",
        source_event_id="same-source-event",
    )
    payload = {"agent_id": agent.scope.agent_id, "evidence": event.model_dump(mode="json")}
    assert request(api, "POST", "/v1/evidence", body=payload).status_code == 202

    duplicate_event = event.model_copy(update={"evidence_id": "retry"})
    duplicate = request(
        api,
        "POST",
        "/v1/evidence",
        body={
            "agent_id": agent.scope.agent_id,
            "evidence": duplicate_event.model_dump(mode="json"),
        },
    )
    conflict_event = duplicate_event.model_copy(update={"outcome": EvidenceOutcome.FAIL})
    conflict = request(
        api,
        "POST",
        "/v1/evidence",
        body={
            "agent_id": agent.scope.agent_id,
            "evidence": conflict_event.model_dump(mode="json"),
        },
    )

    assert duplicate.status_code == 200
    assert duplicate.json_body["status"] == "DUPLICATE"
    assert conflict.status_code == 409
    assert conflict.json_body["error"]["code"] == "EVIDENCE_CONFLICT"
    assert "FAIL" not in conflict.body.decode("utf-8")

    for control in agent.controls:
        if control.control_id == "pii-redaction":
            continue
        remaining = make_evidence(agent, control.control_id)
        assert request(
            api,
            "POST",
            "/v1/evidence",
            body={
                "agent_id": agent.scope.agent_id,
                "evidence": remaining.model_dump(mode="json"),
            },
        ).status_code == 202
    synced = request(
        api,
        "POST",
        f"/v1/agents/{agent.scope.agent_id}/sync?{query_for(agent)}",
    )
    assert synced.json_body["compliance"]["overall_compliance_status"] == "AMBER"
    assert "EVIDENCE_CONFLICT" in synced.json_body["compliance"]["reason_codes"]


def test_unattested_canary_is_rejected_at_the_http_boundary(system) -> None:
    service, _, _, agent = system
    api = ProofLoopApi(service=service, api_key=API_KEY)
    unsafe = make_evidence(agent, "guardrails").model_copy(
        update={"attributes": ()}
    )

    response = request(
        api,
        "POST",
        "/v1/evidence",
        body={
            "agent_id": agent.scope.agent_id,
            "evidence": unsafe.model_dump(mode="json"),
        },
    )

    assert response.status_code == 422
    assert response.json_body["error"]["code"] == "UNSAFE_CANARY_EVIDENCE"


def test_invalid_json_and_cross_boundary_queries_are_customer_safe(system) -> None:
    service, _, _, agent = system
    ingest_all_passes(service, agent)
    service.sync(agent.scope)
    api = ProofLoopApi(service=service, api_key=API_KEY)

    invalid = api.handle(
        method="POST",
        path="/v1/evidence",
        query_string="",
        headers={"X-API-Key": API_KEY},
        body=b'{"raw_invoice":"sensitive value"',
    )
    foreign = request(
        api,
        "GET",
        (
            f"/v1/agents/{agent.scope.agent_id}/compliance"
            "?tenant_id=tenant-b&environment=TEST"
            "&assurance_boundary_id=tenant-b-test"
        ),
    )

    assert invalid.status_code == 400
    assert invalid.json_body["error"]["code"] == "INVALID_REQUEST"
    assert "sensitive value" not in invalid.body.decode("utf-8")
    assert foreign.status_code == 404
    assert foreign.json_body["error"]["code"] == "AGENT_NOT_FOUND"


def test_timeline_query_accepts_explicit_time_range(system) -> None:
    service, _, clock, agent = system
    service.sync(agent.scope)
    api = ProofLoopApi(service=service, api_key=API_KEY)
    start = (clock.now() - timedelta(days=1)).isoformat()
    end = (clock.now() + timedelta(days=1)).isoformat()

    response = request(
        api,
        "GET",
        (
            f"/v1/agents/{agent.scope.agent_id}/timeline?{query_for(agent)}"
            f"&start={start}&end={end}"
        ),
    )

    assert response.status_code == 200
    assert len(response.json_body["items"]) == 1
