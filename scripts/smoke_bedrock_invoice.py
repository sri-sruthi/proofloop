#!/usr/bin/env python3
"""Explicitly guarded real-Bedrock invoice integration smoke.

This command can incur AWS cost. Track C installs it but does not execute it.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _is_successful_smoke(status_code: int, payload: object) -> bool:
    """Require a real model call plus successful workflow and assurance state."""

    if status_code != 200 or not isinstance(payload, dict):
        return False
    usage = payload.get("model_usage")
    compliance = payload.get("compliance")
    evidence = payload.get("evidence")
    return (
        payload.get("workflow_status") == "COMPLETED"
        and isinstance(usage, dict)
        and isinstance(usage.get("model_calls"), int)
        and usage["model_calls"] >= 1
        and isinstance(evidence, list)
        and len(evidence) >= 1
        and isinstance(compliance, dict)
        and compliance.get("overall_compliance_status") == "GREEN"
    )


def main() -> int:
    if os.environ.get("PROOFLOOP_ALLOW_REAL_MODEL_SMOKE", "").lower() != "true":
        print(
            "Real Bedrock smoke is disabled. Set "
            "PROOFLOOP_ALLOW_REAL_MODEL_SMOKE=true only after explicit authorization.",
            file=sys.stderr,
        )
        return 2
    if os.environ.get("PROOFLOOP_MODEL_PROVIDER", "").lower() != "bedrock":
        print("PROOFLOOP_MODEL_PROVIDER must be bedrock.", file=sys.stderr)
        return 2
    required = (
        "PROOFLOOP_API_KEY",
        "PROOFLOOP_BEDROCK_MODEL_ID",
        "PROOFLOOP_BEDROCK_REGION",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("Missing required smoke configuration: " + ", ".join(missing), file=sys.stderr)
        return 2

    repository = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository / "src"))
    from proofloop.infrastructure.composition import build_application

    tenant_id = os.environ.get("PROOFLOOP_DEMO_TENANT_ID", "proofloop-demo")
    environment = os.environ.get("PROOFLOOP_DEMO_ENVIRONMENT", "LOCAL")
    boundary_id = os.environ.get(
        "PROOFLOOP_DEMO_BOUNDARY_ID",
        "proofloop-demo-local-invoices",
    )
    agent_id = os.environ.get("PROOFLOOP_DEMO_AGENT_ID", "invoice-agent")
    payload = {
        "document_id": "synthetic-real-smoke-1",
        "content_type": "TEXT_PLAIN",
        "source_system": "proofloop-authorized-smoke",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "invoice_content": (
            "Synthetic invoice fixture. Vendor Acme Supplies, invoice INV-9, "
            "purchase order PO-1, two widgets at 50 USD plus 5 USD tax, total 105 USD."
        ),
    }
    response = build_application().handle(
        method="POST",
        path=f"/v1/agents/{agent_id}/runs/invoice",
        query_string=(
            f"tenant_id={tenant_id}&environment={environment}"
            f"&assurance_boundary_id={boundary_id}"
        ),
        headers={"X-API-Key": os.environ["PROOFLOOP_API_KEY"]},
        body=json.dumps(payload).encode("utf-8"),
    )
    safe = response.json_body
    print(
        json.dumps(
            {
                "status_code": response.status_code,
                "workflow_status": safe.get("workflow_status"),
                "model_usage": safe.get("model_usage"),
                "compliance_status": safe.get("compliance", {}).get(
                    "overall_compliance_status"
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if _is_successful_smoke(response.status_code, safe) else 1


if __name__ == "__main__":
    raise SystemExit(main())
