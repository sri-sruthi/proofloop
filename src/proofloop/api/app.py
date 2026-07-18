"""Small WSGI-compatible router with API-key auth and generated OpenAPI."""

from __future__ import annotations

import hmac
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, unquote

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.json_schema import JsonSchemaMode, models_json_schema

from proofloop.application.errors import ApplicationError, ErrorCode
from proofloop.application.models import (
    AgentScope,
    ComplianceIncident,
    ComplianceReadModel,
    EvidenceIngestResult,
    EvidenceIngestStatus,
    SyncOutcome,
    TimelineEntry,
)
from proofloop.application.service import ProofLoopService
from proofloop.api.invoice_runs import (
    InvoiceRunPort,
    InvoiceRunRequest,
    InvoiceRunResponse,
)
from proofloop.domain.models import EvidenceEnvelope


_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_AGENT_ROUTE = re.compile(
    r"^/v1/agents/(?P<agent_id>[^/]+)/(?P<resource>sync|compliance|timeline|incidents)$"
)
_INVOICE_RUN_ROUTE = re.compile(
    r"^/v1/agents/(?P<agent_id>[^/]+)/runs/invoice$"
)


class EvidenceSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    agent_id: str
    evidence: EvidenceEnvelope


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    request_id: str
    trace_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class TimelineListResponse(BaseModel):
    items: list[TimelineEntry]


class IncidentListResponse(BaseModel):
    items: list[ComplianceIncident]


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    @property
    def json_body(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


@dataclass(frozen=True)
class _Route:
    method: str
    path: str
    operation_id: str
    summary: str
    public: bool = False


_ROUTES = (
    _Route("GET", "/healthz", "health", "Service health", public=True),
    _Route("GET", "/openapi.json", "openapi", "OpenAPI contract"),
    _Route("POST", "/v1/evidence", "ingestEvidence", "Ingest runtime evidence"),
    _Route(
        "POST",
        "/v1/agents/{agent_id}/sync",
        "syncAgent",
        "Synchronize compliance",
    ),
    _Route(
        "POST",
        "/v1/agents/{agent_id}/runs/invoice",
        "runInvoiceAgent",
        "Run the bounded invoice workflow and synchronize compliance",
    ),
    _Route(
        "GET",
        "/v1/agents/{agent_id}/compliance",
        "getCompliance",
        "Read current compliance",
    ),
    _Route(
        "GET",
        "/v1/agents/{agent_id}/timeline",
        "getTimeline",
        "Read seven-day status timeline",
    ),
    _Route(
        "GET",
        "/v1/agents/{agent_id}/incidents",
        "getIncidents",
        "Read compliance incidents",
    ),
)


class ProofLoopApi:
    """HTTP adapter around `ProofLoopService`; no web framework required."""

    def __init__(
        self,
        *,
        service: ProofLoopService,
        api_key: str | None,
        max_body_bytes: int = 256_000,
        allowed_origin: str | None = None,
        invoice_runner: InvoiceRunPort | None = None,
    ) -> None:
        self._service = service
        self._api_key = api_key
        self._max_body_bytes = max_body_bytes
        self._allowed_origin = allowed_origin
        self._invoice_runner = invoice_runner

    def handle(
        self,
        *,
        method: str,
        path: str,
        query_string: str,
        headers: Mapping[str, str],
        body: bytes,
        request_body_valid: bool = True,
    ) -> ApiResponse:
        normalized_headers = {key.lower(): value for key, value in headers.items()}
        request_id = _correlation_id(
            normalized_headers.get("x-request-id"),
            prefix="request",
        )
        trace_id = _correlation_id(
            normalized_headers.get("x-trace-id"),
            prefix="trace",
        )
        response_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Request-ID": request_id,
            "X-Trace-ID": trace_id,
            "Cache-Control": "no-store",
        }
        request_origin = normalized_headers.get("origin")
        if self._allowed_origin and request_origin == self._allowed_origin:
            response_headers.update(
                {
                    "Access-Control-Allow-Origin": self._allowed_origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": (
                        "X-API-Key, Content-Type, X-Request-ID, X-Trace-ID"
                    ),
                    "Vary": "Origin",
                }
            )

        try:
            if not request_body_valid:
                raise ValueError("request body failed adapter validation")
            if (
                method.upper() == "OPTIONS"
                and "Access-Control-Allow-Origin" in response_headers
            ):
                return ApiResponse(
                    status_code=HTTPStatus.NO_CONTENT,
                    headers=response_headers,
                    body=b"",
                )
            if path != "/healthz":
                self._authenticate(normalized_headers.get("x-api-key"))
            if len(body) > self._max_body_bytes:
                raise ApplicationError(
                    ErrorCode.INVALID_REQUEST,
                    "Request body exceeds the configured size limit.",
                )
            payload, status = self._dispatch(
                method=method.upper(),
                path=path,
                query_string=query_string,
                body=body,
            )
            return _json_response(status, payload, response_headers)
        except ApplicationError as error:
            return _json_response(
                _status_for_error(error.code),
                {
                    "error": {
                        "code": error.code.value,
                        "message": error.message,
                        "request_id": request_id,
                        "trace_id": trace_id,
                    }
                },
                response_headers,
            )
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, ValueError):
            return _json_response(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": {
                        "code": ErrorCode.INVALID_REQUEST.value,
                        "message": "Request validation failed.",
                        "request_id": request_id,
                        "trace_id": trace_id,
                    }
                },
                response_headers,
            )
        except Exception:
            return _json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": {
                        "code": ErrorCode.INTERNAL_ERROR.value,
                        "message": "The request could not be completed safely.",
                        "request_id": request_id,
                        "trace_id": trace_id,
                    }
                },
                response_headers,
            )

    def __call__(self, environ: Mapping[str, Any], start_response) -> Iterable[bytes]:
        content_length_text = environ.get("CONTENT_LENGTH") or "0"
        request_body_valid = True
        try:
            content_length = int(content_length_text)
        except ValueError:
            content_length = 0
            request_body_valid = False
        if content_length < 0 or content_length > self._max_body_bytes:
            request_body_valid = False
        stream = environ.get("wsgi.input")
        body = (
            stream.read(content_length)
            if request_body_valid and stream is not None
            else b""
        )
        headers = {
            key[5:].replace("_", "-"): str(value)
            for key, value in environ.items()
            if key.startswith("HTTP_")
        }
        response = self.handle(
            method=str(environ.get("REQUEST_METHOD", "GET")),
            path=str(environ.get("PATH_INFO", "/")),
            query_string=str(environ.get("QUERY_STRING", "")),
            headers=headers,
            body=body,
            request_body_valid=request_body_valid,
        )
        response_headers = list(response.headers.items())
        response_headers.append(("Content-Length", str(len(response.body))))
        start_response(
            f"{response.status_code} {HTTPStatus(response.status_code).phrase}",
            response_headers,
        )
        return (response.body,)

    def _authenticate(self, candidate: str | None) -> None:
        if not self._api_key:
            raise ApplicationError(
                ErrorCode.AUTHENTICATION_NOT_CONFIGURED,
                "API-key authentication is not configured.",
            )
        if candidate is None:
            raise ApplicationError(
                ErrorCode.AUTHENTICATION_REQUIRED,
                "An API key is required for this endpoint.",
            )
        if not hmac.compare_digest(candidate, self._api_key):
            raise ApplicationError(
                ErrorCode.AUTHENTICATION_FAILED,
                "The supplied API key is not valid.",
            )

    def _dispatch(
        self,
        *,
        method: str,
        path: str,
        query_string: str,
        body: bytes,
    ) -> tuple[Any, int]:
        if method == "GET" and path == "/healthz":
            return {"status": "ok"}, HTTPStatus.OK
        if method == "GET" and path == "/openapi.json":
            return _generate_openapi(), HTTPStatus.OK
        if method == "POST" and path == "/v1/evidence":
            submission = EvidenceSubmission.model_validate(
                json.loads(body.decode("utf-8"))
            )
            workflow = submission.evidence.workflow
            scope = AgentScope(
                tenant_id=workflow.tenant_id,
                environment=workflow.environment,
                assurance_boundary_id=workflow.assurance_boundary_id,
                agent_id=submission.agent_id,
            )
            result = self._service.ingest_evidence(scope, submission.evidence)
            status = (
                HTTPStatus.ACCEPTED
                if result.status is EvidenceIngestStatus.ACCEPTED
                else HTTPStatus.OK
            )
            return result.model_dump(mode="json"), status

        invoice_run = _INVOICE_RUN_ROUTE.match(path)
        if invoice_run is not None and method == "POST":
            if self._invoice_runner is None:
                raise ApplicationError(
                    ErrorCode.INTEGRATION_NOT_CONFIGURED,
                    "The invoice workflow integration is not configured.",
                )
            agent_id = unquote(invoice_run.group("agent_id"))
            query = parse_qs(query_string, keep_blank_values=True)
            scope = _scope_from_query(agent_id, query)
            request = InvoiceRunRequest.model_validate(
                json.loads(body.decode("utf-8"))
            )
            response = self._invoice_runner.run_invoice(scope, request)
            return response.model_dump(mode="json"), HTTPStatus.OK

        matched = _AGENT_ROUTE.match(path)
        if matched is not None:
            agent_id = unquote(matched.group("agent_id"))
            resource = matched.group("resource")
            query = parse_qs(query_string, keep_blank_values=True)
            scope = _scope_from_query(agent_id, query)
            if resource == "sync" and method == "POST":
                outcome = self._service.sync(scope)
                return outcome.model_dump(mode="json"), HTTPStatus.OK
            if resource == "compliance" and method == "GET":
                value = self._service.get_compliance(scope)
                return value.model_dump(mode="json"), HTTPStatus.OK
            if resource == "timeline" and method == "GET":
                end = _query_datetime(query, "end") or self._service.now()
                start = _query_datetime(query, "start") or end - timedelta(days=7)
                timeline_items = self._service.list_timeline(
                    scope,
                    start=start,
                    end=end,
                )
                return {
                    "items": [
                        item.model_dump(mode="json") for item in timeline_items
                    ]
                }, HTTPStatus.OK
            if resource == "incidents" and method == "GET":
                incident_items = self._service.list_incidents(scope)
                return {
                    "items": [
                        item.model_dump(mode="json") for item in incident_items
                    ]
                }, HTTPStatus.OK

        raise ApplicationError(
            ErrorCode.NOT_FOUND,
            "No API route matches this request.",
        )


def _scope_from_query(
    agent_id: str,
    query: Mapping[str, list[str]],
) -> AgentScope:
    return AgentScope.model_validate(
        {
            "tenant_id": _one_query_value(query, "tenant_id"),
            "environment": _one_query_value(query, "environment"),
            "assurance_boundary_id": _one_query_value(
                query,
                "assurance_boundary_id",
            ),
            "agent_id": agent_id,
        }
    )


def _one_query_value(query: Mapping[str, list[str]], name: str) -> str:
    values = query.get(name)
    if values is None or len(values) != 1 or not values[0]:
        raise ValueError(f"one non-empty {name} query parameter is required")
    return values[0]


def _query_datetime(
    query: Mapping[str, list[str]],
    name: str,
) -> datetime | None:
    values = query.get(name)
    if values is None:
        return None
    if len(values) != 1:
        raise ValueError(f"only one {name} query parameter is allowed")
    text = values[0].replace(" ", "+").replace("Z", "+00:00")
    value = datetime.fromisoformat(text)
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be UTC-aware")
    return value


def _correlation_id(candidate: str | None, *, prefix: str) -> str:
    if candidate and _SAFE_CORRELATION_ID.fullmatch(candidate):
        return candidate
    return f"{prefix}-{uuid.uuid4()}"


def _status_for_error(code: ErrorCode) -> HTTPStatus:
    return {
        ErrorCode.AUTHENTICATION_REQUIRED: HTTPStatus.UNAUTHORIZED,
        ErrorCode.AUTHENTICATION_FAILED: HTTPStatus.FORBIDDEN,
        ErrorCode.AUTHENTICATION_NOT_CONFIGURED: HTTPStatus.SERVICE_UNAVAILABLE,
        ErrorCode.INTEGRATION_NOT_CONFIGURED: HTTPStatus.SERVICE_UNAVAILABLE,
        ErrorCode.AGENT_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ErrorCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
        ErrorCode.EVIDENCE_CONFLICT: HTTPStatus.CONFLICT,
        ErrorCode.BOUNDARY_MISMATCH: HTTPStatus.UNPROCESSABLE_ENTITY,
        ErrorCode.WORKFLOW_MISMATCH: HTTPStatus.UNPROCESSABLE_ENTITY,
        ErrorCode.EVIDENCE_NOT_DECLARED: HTTPStatus.UNPROCESSABLE_ENTITY,
        ErrorCode.UNSAFE_EVIDENCE_PAYLOAD: HTTPStatus.UNPROCESSABLE_ENTITY,
        ErrorCode.UNSAFE_CANARY_EVIDENCE: HTTPStatus.UNPROCESSABLE_ENTITY,
        ErrorCode.INVALID_REQUEST: HTTPStatus.BAD_REQUEST,
        ErrorCode.INTERNAL_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
    }[code]


def _json_response(
    status: int | HTTPStatus,
    payload: Any,
    headers: dict[str, str],
) -> ApiResponse:
    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return ApiResponse(status_code=int(status), headers=headers, body=body)


def _generate_openapi() -> dict[str, Any]:
    schema_models: tuple[tuple[type[BaseModel], JsonSchemaMode], ...] = (
        (EvidenceSubmission, "validation"),
        (InvoiceRunRequest, "validation"),
        (InvoiceRunResponse, "serialization"),
        (EvidenceIngestResult, "serialization"),
        (SyncOutcome, "serialization"),
        (ComplianceReadModel, "serialization"),
        (TimelineEntry, "serialization"),
        (ComplianceIncident, "serialization"),
        (TimelineListResponse, "serialization"),
        (IncidentListResponse, "serialization"),
        (ErrorEnvelope, "serialization"),
    )
    _, generated_schema = models_json_schema(
        schema_models,
        ref_template="#/components/schemas/{model}",
    )
    schemas = generated_schema["$defs"]

    paths: dict[str, Any] = {}
    for route in _ROUTES:
        operation = _openapi_operation(route)
        paths.setdefault(route.path, {})[route.method.lower()] = operation
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "ProofLoop API",
            "version": "0.1.0",
            "description": "Runtime-to-compliance evidence assurance vertical slice.",
        },
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            }
        },
    }


def _openapi_operation(route: _Route) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": route.operation_id,
        "summary": route.summary,
        "responses": _success_responses(route),
    }
    if route.path.startswith("/v1/agents/{agent_id}/"):
        operation["parameters"] = _agent_parameters(
            include_time_range=route.path.endswith("/timeline")
        )
    if route.path == "/v1/evidence":
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/EvidenceSubmission"}
                }
            },
        }
    if route.path == "/v1/agents/{agent_id}/runs/invoice":
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/InvoiceRunRequest"}
                }
            },
        }
    if not route.public:
        operation["security"] = [{"ApiKeyAuth": []}]
        operation["responses"].update(_error_responses(route))
    return operation


def _success_responses(route: _Route) -> dict[str, Any]:
    if route.path == "/healthz":
        return {
            "200": _json_schema_response(
                "Service is healthy.",
                {
                    "type": "object",
                    "properties": {"status": {"const": "ok"}},
                    "required": ["status"],
                    "additionalProperties": False,
                },
            )
        }
    if route.path == "/openapi.json":
        return {
            "200": _json_schema_response(
                "OpenAPI contract.",
                {"type": "object"},
            )
        }
    if route.path == "/v1/evidence":
        schema = {"$ref": "#/components/schemas/EvidenceIngestResult"}
        return {
            "200": _json_schema_response(
                "Duplicate evidence already recorded.",
                schema,
            ),
            "202": _json_schema_response("Evidence accepted.", schema),
        }
    response_schema = {
        "/v1/agents/{agent_id}/sync": "SyncOutcome",
        "/v1/agents/{agent_id}/runs/invoice": "InvoiceRunResponse",
        "/v1/agents/{agent_id}/compliance": "ComplianceReadModel",
        "/v1/agents/{agent_id}/timeline": "TimelineListResponse",
        "/v1/agents/{agent_id}/incidents": "IncidentListResponse",
    }[route.path]
    return {
        "200": _json_schema_response(
            "Successful response.",
            {"$ref": f"#/components/schemas/{response_schema}"},
        )
    }


def _error_responses(route: _Route) -> dict[str, Any]:
    statuses: dict[str, str] = {
        "400": "Request validation failed.",
        "401": "API key is required.",
        "403": "API key is invalid.",
        "500": "Internal request failure.",
        "503": "Authentication is not configured.",
    }
    if route.path.startswith("/v1/agents/"):
        statuses["404"] = "Agent or route was not found."
    if route.path in {
        "/v1/evidence",
        "/v1/agents/{agent_id}/runs/invoice",
    }:
        statuses.update(
            {
                "409": "Evidence conflicts with an existing idempotency record.",
                "422": "Evidence violates an assurance boundary or safety contract.",
            }
        )
    return {
        status: _json_schema_response(
            description,
            {"$ref": "#/components/schemas/ErrorEnvelope"},
        )
        for status, description in statuses.items()
    }


def _json_schema_response(description: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": schema}},
    }


def _agent_parameters(*, include_time_range: bool) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = [
        {
            "name": "agent_id",
            "in": "path",
            "required": True,
            "schema": {"type": "string", "minLength": 1},
        },
        {
            "name": "tenant_id",
            "in": "query",
            "required": True,
            "schema": {"type": "string", "minLength": 1},
        },
        {
            "name": "environment",
            "in": "query",
            "required": True,
            "schema": {"$ref": "#/components/schemas/Environment"},
        },
        {
            "name": "assurance_boundary_id",
            "in": "query",
            "required": True,
            "schema": {"type": "string", "minLength": 1},
        },
    ]
    if include_time_range:
        parameters.extend(
            (
                {
                    "name": "start",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "format": "date-time"},
                },
                {
                    "name": "end",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "format": "date-time"},
                },
            )
        )
    return parameters
