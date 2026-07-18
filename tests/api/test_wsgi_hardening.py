from __future__ import annotations

import json
from typing import Any

import pytest

from proofloop.api.app import ProofLoopApi


API_KEY = "test-api-key"


class ReadSpy:
    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload
        self.calls: list[int] = []

    def read(self, size: int) -> bytes:
        self.calls.append(size)
        return self.payload[:size]


@pytest.mark.parametrize("content_length", ["-1", "17", "not-an-integer"])
def test_wsgi_rejects_invalid_declared_lengths_without_reading(
    system,
    content_length: str,
) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY, max_body_bytes=16)
    stream = ReadSpy(b"sensitive body that must never be read")
    captured: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    chunks = api(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/evidence",
            "QUERY_STRING": "",
            "CONTENT_LENGTH": content_length,
            "HTTP_X_API_KEY": API_KEY,
            "HTTP_X_REQUEST_ID": "wsgi-request-1",
            "HTTP_X_TRACE_ID": "wsgi-trace-1",
            "wsgi.input": stream,
        },
        start_response,
    )

    payload = json.loads(b"".join(chunks))
    assert captured["status"] == "400 Bad Request"
    assert captured["headers"]["X-Request-ID"] == "wsgi-request-1"
    assert payload["error"] == {
        "code": "INVALID_REQUEST",
        "message": "Request validation failed.",
        "request_id": "wsgi-request-1",
        "trace_id": "wsgi-trace-1",
    }
    assert stream.calls == []


def test_wsgi_reads_only_the_validated_declared_length(system) -> None:
    service, _, _, _ = system
    api = ProofLoopApi(service=service, api_key=API_KEY, max_body_bytes=16)
    stream = ReadSpy(b"{}ignored")
    status: list[str] = []

    list(
        api(
            {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/v1/evidence",
                "QUERY_STRING": "",
                "CONTENT_LENGTH": "2",
                "HTTP_X_API_KEY": API_KEY,
                "wsgi.input": stream,
            },
            lambda value, _: status.append(value),
        )
    )

    assert status == ["400 Bad Request"]
    assert stream.calls == [2]
