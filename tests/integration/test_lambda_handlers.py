from __future__ import annotations

import base64
import json

from proofloop.api.app import ApiResponse
from proofloop.infrastructure import lambda_handler, scheduled_handler


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def handle(self, **kwargs):
        self.calls.append(kwargs)
        return ApiResponse(
            status_code=202,
            headers={"Content-Type": "application/json", "X-Request-ID": "request-1"},
            body=b'{"status":"ACCEPTED"}',
        )


def test_http_api_v2_event_is_adapted_without_framework_or_payload_logging(monkeypatch) -> None:
    fake = FakeApi()
    monkeypatch.setattr(lambda_handler, "_application", fake)
    payload = b'{"metadata":"safe"}'
    event = {
        "version": "2.0",
        "rawPath": "/v1/evidence",
        "rawQueryString": "",
        "headers": {"x-api-key": "secret", "x-request-id": "request-1"},
        "body": base64.b64encode(payload).decode("ascii"),
        "isBase64Encoded": True,
        "requestContext": {"http": {"method": "POST"}},
    }

    response = lambda_handler.handler(event, None)

    assert response["statusCode"] == 202
    assert json.loads(response["body"])["status"] == "ACCEPTED"
    assert fake.calls[0]["body"] == payload
    assert fake.calls[0]["path"] == "/v1/evidence"


class FakeSyncResult:
    class Compliance:
        overall_compliance_status = type("Status", (), {"value": "GREEN"})()

    compliance = Compliance()


class FakeService:
    def __init__(self) -> None:
        self.scopes = ("scope-a", "scope-b")
        self.synced: list[str] = []

    def list_agent_scopes(self):
        return self.scopes

    def sync(self, scope):
        self.synced.append(scope)
        return FakeSyncResult()


def test_scheduled_handler_syncs_each_registered_scope_once(monkeypatch) -> None:
    service = FakeService()
    monkeypatch.setattr(scheduled_handler, "_service", service)

    result = scheduled_handler.scheduled_handler(
        {"source": "proofloop.reconciliation"},
        None,
    )

    assert result == {"agents_seen": 2, "agents_synced": 2, "errors": 0}
    assert service.synced == ["scope-a", "scope-b"]
