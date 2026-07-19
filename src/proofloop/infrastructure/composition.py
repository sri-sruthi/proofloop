"""Local/AWS composition root. SDK construction is isolated to this module."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable

from proofloop.agents.contracts import DuplicateStatus
from proofloop.agents.execution import ExecutionLimits
from proofloop.agents.mcp.tool_specs import (
    InMemoryDuplicateCheckTool,
    InMemoryHumanReviewTool,
    InMemoryPurchaseOrderTool,
    InMemoryVendorTool,
    PurchaseOrderRecord,
    VendorRecord,
)
from proofloop.agents.model_provider import (
    FakeModelProvider,
    FakeStep,
    ModelProvider,
    StopReason,
)
from proofloop.agents.providers import BedrockConverseProvider, BedrockProviderConfig
from proofloop.api.app import ProofLoopApi
from proofloop.api.invoice_runs import InvoiceRunPort, InvoiceRunRequest
from proofloop.application.models import AgentScope, IncidentSlaPolicy
from proofloop.application.scenario import build_demo_agent, seed_fresh_passes
from proofloop.application.service import ProofLoopService
from proofloop.domain.models import Environment
from proofloop.infrastructure.dynamodb import DynamoProofLoopStore
from proofloop.infrastructure.agent_integration import (
    AgentIntegrationSettings,
    InvoiceAgentRunner,
    build_integrated_invoice_agent,
    run_safe_extraction_canary,
)
from proofloop.infrastructure.memory import InMemoryProofLoopStore, SystemClock


def build_service(
    *,
    store: Any | None = None,
    clock: Any | None = None,
    seed_demo: bool | None = None,
) -> ProofLoopService:
    selected_store = store or _store_from_environment()
    selected_clock = clock or SystemClock()
    service = ProofLoopService(
        agents=selected_store,
        evidence=selected_store,
        compliance=selected_store,
        timeline=selected_store,
        incidents=selected_store,
        state=selected_store,
        clock=selected_clock,
        incident_sla=IncidentSlaPolicy(
            amber_after=timedelta(
                hours=float(os.environ.get("PROOFLOOP_AMBER_SLA_HOURS", "24"))
            ),
            red_after=timedelta(
                hours=float(os.environ.get("PROOFLOOP_RED_SLA_HOURS", "1"))
            ),
        ),
    )
    local_memory_default = store is not None or not os.environ.get(
        "PROOFLOOP_EVIDENCE_TABLE_NAME"
    )
    should_seed = _env_flag(
        "PROOFLOOP_SEED_DEMO",
        default=local_memory_default,
    )
    if seed_demo is not None:
        should_seed = seed_demo
    if should_seed:
        agent = build_demo_agent(
            tenant_id=os.environ.get("PROOFLOOP_DEMO_TENANT_ID", "proofloop-demo"),
            environment=Environment(
                os.environ.get("PROOFLOOP_DEMO_ENVIRONMENT", "LOCAL")
            ),
            assurance_boundary_id=os.environ.get(
                "PROOFLOOP_DEMO_BOUNDARY_ID",
                "proofloop-demo-local-invoices",
            ),
            agent_id=os.environ.get("PROOFLOOP_DEMO_AGENT_ID", "invoice-agent"),
        )
        newly_registered = service.register_agent(agent)
        if newly_registered:
            seed_fresh_passes(
                service,
                agent,
                observed_at=selected_clock.now(),
                source_suffix="bootstrap",
            )
    return service


def build_application(
    *,
    service: ProofLoopService | None = None,
    invoice_runner: InvoiceRunPort | None = None,
    bedrock_client: Any | None = None,
) -> ProofLoopApi:
    selected_service = service or build_service(seed_demo=False)
    selected_runner = invoice_runner
    if selected_runner is None and service is None:
        selected_runner = build_invoice_runner(
            service=selected_service,
            bedrock_client=bedrock_client,
        )
    return ProofLoopApi(
        service=selected_service,
        api_key=os.environ.get("PROOFLOOP_API_KEY"),
        allowed_origin=os.environ.get(
            "PROOFLOOP_ALLOWED_ORIGIN",
            "http://localhost:8000",
        ),
        invoice_runner=selected_runner,
    )


def build_invoice_runner(
    *,
    service: ProofLoopService,
    bedrock_client: Any | None = None,
) -> InvoiceAgentRunner:
    """Compose the agent bridge; boto3 is constructed only for Bedrock mode."""

    provider_mode = os.environ.get("PROOFLOOP_MODEL_PROVIDER", "fake").strip().lower()
    model_id = os.environ.get("PROOFLOOP_BEDROCK_MODEL_ID")
    limits = ExecutionLimits(
        max_model_calls=int(os.environ.get("PROOFLOOP_MAX_MODEL_CALLS", "2")),
        max_retries=int(os.environ.get("PROOFLOOP_MAX_RETRIES", "1")),
        timeout=timedelta(
            seconds=float(os.environ.get("PROOFLOOP_MODEL_TIMEOUT_SECONDS", "30"))
        ),
    )
    provider_factory: Callable[[InvoiceRunRequest], ModelProvider]
    if provider_mode == "fake":
        model_version = os.environ.get("PROOFLOOP_MODEL_VERSION", "fake-model-v0")

        def fake_provider_factory(request: InvoiceRunRequest) -> ModelProvider:
            return _fake_provider(
                request,
                provider_id=model_version,
            )

        provider_factory = fake_provider_factory
    elif provider_mode == "bedrock":
        if not model_id:
            raise ValueError("PROOFLOOP_BEDROCK_MODEL_ID is required in Bedrock mode")
        model_version = os.environ.get("PROOFLOOP_MODEL_VERSION", model_id)
        region = _required_environment("PROOFLOOP_BEDROCK_REGION")
        client = bedrock_client or _bedrock_runtime_client(
            region,
            timeout_seconds=limits.timeout.total_seconds(),
        )
        provider_config = BedrockProviderConfig(
            model_id=model_id,
            provider_id=model_version,
        )

        def bedrock_provider_factory(_request: InvoiceRunRequest) -> ModelProvider:
            return BedrockConverseProvider(
                client=client,
                config=provider_config,
            )

        provider_factory = bedrock_provider_factory
    else:
        raise ValueError("PROOFLOOP_MODEL_PROVIDER must be either fake or bedrock")

    settings = _integration_settings(model_version)
    return InvoiceAgentRunner(
        service=service,
        settings=settings,
        provider_factory=provider_factory,
        limits=limits,
        max_output_tokens=int(
            os.environ.get("PROOFLOOP_MAX_OUTPUT_TOKENS", "2000")
        ),
        purchase_order_tool=InMemoryPurchaseOrderTool(
            {
                "PO-1": PurchaseOrderRecord(
                    po_number="PO-1",
                    vendor_id="V1",
                    vendor_name="Acme Supplies",
                    currency="USD",
                    total=Decimal("105.00"),
                    status="OPEN",
                )
            }
        ),
        vendor_tool=InMemoryVendorTool(
            (
                VendorRecord(
                    vendor_id="V1",
                    vendor_name="Acme Supplies",
                    active=True,
                ),
            )
        ),
        duplicate_tool=InMemoryDuplicateCheckTool(DuplicateStatus.NOT_DUPLICATE),
        human_review_tool=InMemoryHumanReviewTool(),
        seed_safe_canary=_env_flag("PROOFLOOP_SEED_SAFE_CANARY", default=True),
    )


def build_scheduled_service() -> ProofLoopService:
    """Compose scheduled reconciliation with the same integrated definition."""

    service = build_service(seed_demo=False)
    model_version = os.environ.get(
        "PROOFLOOP_MODEL_VERSION",
        os.environ.get("PROOFLOOP_BEDROCK_MODEL_ID", "fake-model-v0"),
    )
    settings = _integration_settings(model_version)
    agent = build_integrated_invoice_agent(settings)
    newly_registered = service.register_agent(agent)
    if newly_registered and _env_flag("PROOFLOOP_SEED_SAFE_CANARY", default=True):
        service.ingest_evidence(
            agent.scope,
            run_safe_extraction_canary(
                settings=settings,
                agent=agent,
                observed_at=service.now(),
            ),
        )
    return service


def build_scheduled_canary_emitter(
    service: ProofLoopService,
) -> Callable[[AgentScope], None]:
    """Build the model-free, independently scheduled safe-canary emitter."""

    model_version = os.environ.get(
        "PROOFLOOP_MODEL_VERSION",
        os.environ.get("PROOFLOOP_BEDROCK_MODEL_ID", "fake-model-v0"),
    )
    settings = _integration_settings(model_version)
    agent = build_integrated_invoice_agent(settings)

    def emit(scope: AgentScope) -> None:
        if scope != agent.scope:
            return
        observed_at = service.now()
        service.ingest_evidence(
            scope,
            run_safe_extraction_canary(
                settings=settings,
                agent=agent,
                observed_at=observed_at,
                event_label=f"scheduled-{observed_at.isoformat()}",
            ),
        )

    return emit


def _integration_settings(model_version: str) -> AgentIntegrationSettings:
    return AgentIntegrationSettings(
        tenant_id=os.environ.get("PROOFLOOP_DEMO_TENANT_ID", "proofloop-demo"),
        environment=Environment(
            os.environ.get("PROOFLOOP_DEMO_ENVIRONMENT", "LOCAL")
        ),
        assurance_boundary_id=os.environ.get(
            "PROOFLOOP_DEMO_BOUNDARY_ID",
            "proofloop-demo-local-invoices",
        ),
        agent_id=os.environ.get("PROOFLOOP_DEMO_AGENT_ID", "invoice-agent"),
        workflow_id=os.environ.get(
            "PROOFLOOP_AGENT_WORKFLOW_ID",
            "integrated-invoice-workflow",
        ),
        execution_id=os.environ.get(
            "PROOFLOOP_AGENT_EXECUTION_ID",
            "invoice-runtime",
        ),
        trace_id=os.environ.get(
            "PROOFLOOP_AGENT_TRACE_ID",
            "invoice-agent-assurance",
        ),
        model_version=model_version,
        runtime_config_version=os.environ.get(
            "PROOFLOOP_RUNTIME_CONFIG_VERSION",
            "invoice-runtime-v1",
        ),
    )


def _store_from_environment() -> Any:
    table_name = os.environ.get("PROOFLOOP_EVIDENCE_TABLE_NAME")
    if not table_name:
        return InMemoryProofLoopStore()
    import boto3  # type: ignore[import-not-found,import-untyped]  # Lambda runtime dep

    table = boto3.resource("dynamodb").Table(table_name)
    # A transform-free low-level client for TransactWriteItems: the resource
    # client (table.meta.client) re-serializes already-encoded transaction items
    # and double-encodes the keys, which DynamoDB rejects as a PK type mismatch.
    transact_client = boto3.client("dynamodb")
    return DynamoProofLoopStore(table, transact_client=transact_client)


def _bedrock_runtime_client(region: str, *, timeout_seconds: float) -> Any:
    import boto3  # type: ignore[import-not-found,import-untyped]  # Lambda runtime dep
    from botocore.config import Config  # type: ignore[import-not-found,import-untyped]

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(
            connect_timeout=timeout_seconds,
            read_timeout=timeout_seconds,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )


def _fake_provider(
    request: InvoiceRunRequest,
    *,
    provider_id: str,
) -> FakeModelProvider:
    payload = json.dumps(
        {
            "document_id": request.document_id,
            "vendor_name": "Acme Supplies",
            "vendor_id": "V1",
            "invoice_number": "INV-9",
            "invoice_date": "2026-07-10T00:00:00Z",
            "po_number": "PO-1",
            "currency": "USD",
            "line_items": [
                {
                    "description": "Widgets",
                    "quantity": "2",
                    "unit_price": "50.00",
                    "tax": "5.00",
                    "line_total": "105.00",
                }
            ],
            "subtotal": "100.00",
            "tax": "5.00",
            "total": "105.00",
            "status": "COMPLETE",
            "model_reported_confidence": 0.95,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return FakeModelProvider(
        steps=(
            FakeStep(
                kind="response",
                raw_output=payload,
                stop_reason=StopReason.COMPLETED,
                input_tokens=120,
                output_tokens=40,
                provider_id=provider_id,
            ),
        )
    )


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
