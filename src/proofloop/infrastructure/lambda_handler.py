"""AWS Lambda HTTP API v2 adapter for the framework-free ProofLoop API."""

from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any

from proofloop.api.app import ProofLoopApi
from proofloop.infrastructure.composition import build_application


logger = logging.getLogger(__name__)
_application: ProofLoopApi | None = None


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    global _application
    if _application is None:
        _application = build_application()
    body_text = event.get("body") or ""
    request_body_valid = True
    try:
        body = (
            base64.b64decode(body_text, validate=True)
            if event.get("isBase64Encoded")
            else str(body_text).encode("utf-8")
        )
    except (binascii.Error, TypeError, ValueError):
        body = b""
        request_body_valid = False
    headers = {
        str(key): str(value) for key, value in (event.get("headers") or {}).items()
    }
    response = _application.handle(
        method=str(
            event.get("requestContext", {}).get("http", {}).get("method", "GET")
        ),
        path=str(event.get("rawPath", "/")),
        query_string=str(event.get("rawQueryString", "")),
        headers=headers,
        body=body,
        request_body_valid=request_body_valid,
    )
    logger.info(
        json.dumps(
            {
                "event": "http_request_completed",
                "path": event.get("rawPath", "/"),
                "status_code": response.status_code,
                "request_id": response.headers.get("X-Request-ID"),
            },
            separators=(",", ":"),
        )
    )
    return {
        "statusCode": response.status_code,
        "headers": response.headers,
        "body": response.body.decode("utf-8"),
        "isBase64Encoded": False,
    }
