from __future__ import annotations

from typing import Any

from proofloop.api.app import ProofLoopApi

from .test_api import API_KEY, request


def _parameters(operation: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (parameter["in"], parameter["name"]): parameter
        for parameter in operation["parameters"]
    }


def _assert_refs_resolve(document: dict[str, Any], value: Any) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if reference is not None:
            assert reference.startswith("#/components/schemas/")
            assert reference.rsplit("/", 1)[-1] in document["components"]["schemas"]
        for nested in value.values():
            _assert_refs_resolve(document, nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_refs_resolve(document, nested)


def test_openapi_exposes_resolvable_customer_contract_schemas(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY)

    document = request(api, "GET", "/openapi.json").json_body

    assert document["openapi"] == "3.1.0"
    assert set(document["components"]["schemas"]) >= {
        "EvidenceSubmission",
        "ComplianceReadModel",
        "TimelineEntry",
        "ComplianceIncident",
        "ErrorEnvelope",
    }
    _assert_refs_resolve(document, document)


def test_openapi_declares_evidence_body_statuses_and_error_envelopes(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY)

    operation = request(api, "GET", "/openapi.json").json_body["paths"][
        "/v1/evidence"
    ]["post"]

    assert operation["security"] == [{"ApiKeyAuth": []}]
    assert operation["requestBody"]["required"] is True
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EvidenceSubmission"
    }
    assert set(operation["responses"]) >= {
        "200",
        "202",
        "400",
        "401",
        "403",
        "409",
        "422",
    }
    for status in ("400", "401", "403", "409", "422"):
        assert operation["responses"][status]["content"]["application/json"][
            "schema"
        ] == {"$ref": "#/components/schemas/ErrorEnvelope"}


def test_openapi_declares_agent_path_and_scope_query_parameters(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY)
    document = request(api, "GET", "/openapi.json").json_body

    for path, method in (
        ("/v1/agents/{agent_id}/sync", "post"),
        ("/v1/agents/{agent_id}/compliance", "get"),
        ("/v1/agents/{agent_id}/timeline", "get"),
        ("/v1/agents/{agent_id}/incidents", "get"),
    ):
        operation = document["paths"][path][method]
        parameters = _parameters(operation)
        assert parameters[("path", "agent_id")]["required"] is True
        for name in ("tenant_id", "environment", "assurance_boundary_id"):
            assert parameters[("query", name)]["required"] is True
        assert operation["security"] == [{"ApiKeyAuth": []}]
        assert "200" in operation["responses"]
        assert {"400", "401", "403", "404"}.issubset(operation["responses"])

    timeline_parameters = _parameters(
        document["paths"]["/v1/agents/{agent_id}/timeline"]["get"]
    )
    for name in ("start", "end"):
        parameter = timeline_parameters[("query", name)]
        assert parameter["required"] is False
        assert parameter["schema"]["format"] == "date-time"


def test_openapi_success_responses_reference_the_returned_models(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY)
    paths = request(api, "GET", "/openapi.json").json_body["paths"]

    assert paths["/v1/agents/{agent_id}/compliance"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ComplianceReadModel"
    }
    assert paths["/v1/agents/{agent_id}/timeline"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/TimelineListResponse"
    }
    assert paths["/v1/agents/{agent_id}/incidents"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/IncidentListResponse"
    }
