"""EventBridge five-minute reconciliation entry point."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from proofloop.application.models import AgentScope
from proofloop.application.service import ProofLoopService
from proofloop.infrastructure.composition import (
    build_scheduled_canary_emitter,
    build_scheduled_service,
)


logger = logging.getLogger(__name__)
_service: ProofLoopService | None = None
_canary_emitter: Callable[[AgentScope], None] | None = None


def scheduled_handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    global _canary_emitter, _service
    if _service is None:
        _service = build_scheduled_service()
        _canary_emitter = build_scheduled_canary_emitter(_service)
    scopes = tuple(_service.list_agent_scopes())
    synced = 0
    errors = 0
    for scope in scopes:
        try:
            if _canary_emitter is not None:
                _canary_emitter(scope)
            result = _service.sync(scope)
            synced += 1
            status = result.compliance.overall_compliance_status.value
            logger.info(
                json.dumps(
                    {"event": "scheduled_sync_completed", "status": status},
                    separators=(",", ":"),
                )
            )
        except Exception:
            errors += 1
            logger.error(
                json.dumps(
                    {"event": "scheduled_sync_failed"},
                    separators=(",", ":"),
                )
            )
    if errors:
        raise RuntimeError(
            "scheduled reconciliation failed for "
            f"{errors} of {len(scopes)} agent scopes"
        )
    return {"agents_seen": len(scopes), "agents_synced": synced, "errors": errors}
