from __future__ import annotations

import json

from proofloop.api.app import ProofLoopApi
from proofloop.infrastructure import lambda_handler


def test_malformed_base64_returns_safe_api_error_with_correlation_ids(monkeypatch) -> None:
    api = ProofLoopApi(service=object(), api_key="test-api-key")  # type: ignore[arg-type]
    monkeypatch.setattr(lambda_handler, "_application", api)
    event = {
        "version": "2.0",
        "rawPath": "/v1/evidence",
        "rawQueryString": "",
        "headers": {
            "x-api-key": "test-api-key",
            "x-request-id": "lambda-request-1",
            "x-trace-id": "lambda-trace-1",
        },
        "body": "%%%definitely-not-base64%%%",
        "isBase64Encoded": True,
        "requestContext": {"http": {"method": "POST"}},
    }

    response = lambda_handler.handler(event, None)

    assert response["statusCode"] == 400
    assert response["headers"]["X-Request-ID"] == "lambda-request-1"
    assert response["headers"]["X-Trace-ID"] == "lambda-trace-1"
    assert json.loads(response["body"]) == {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "Request validation failed.",
            "request_id": "lambda-request-1",
            "trace_id": "lambda-trace-1",
        }
    }
    assert response["isBase64Encoded"] is False
