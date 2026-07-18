"""Local WSGI server entry point for ProofLoop."""

from __future__ import annotations

import os
from wsgiref.simple_server import make_server

from proofloop.infrastructure.composition import build_application


def main() -> None:
    host = os.environ.get("PROOFLOOP_HOST", "127.0.0.1")
    port = int(os.environ.get("PROOFLOOP_PORT", "8080"))
    app = build_application()
    with make_server(host, port, app) as server:
        print(f"ProofLoop listening on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
