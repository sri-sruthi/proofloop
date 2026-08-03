"""Synchronous MCP-client adapters for ProofLoop's invoice tools.

The reconciliation workflow calls its tools through the ``PurchaseOrderTool`` /
``VendorTool`` / ``DuplicateCheckTool`` / ``HumanReviewTool`` protocols defined
in ``tool_specs`` and is fully **synchronous**. The MCP client API is
**asynchronous**. ``MCPToolClient`` bridges the two: it runs a single
``ClientSession`` on a dedicated background event-loop thread and exposes
blocking calls, so the existing synchronous workflow can drive live MCP tools
without a single change to its orchestration code.

The adapter objects returned by ``purchase_order_tool()`` etc. structurally
satisfy the existing tool ``Protocol``s, which is exactly why they drop straight
into ``run_invoice_workflow``.
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.types import CallToolResult

from proofloop.agents.mcp.tool_specs import (
    DuplicateCheckResult,
    DuplicateQuery,
    HumanReviewRequest,
    HumanReviewTicket,
    PurchaseOrderQuery,
    PurchaseOrderRecord,
    ToolError,
    VendorQuery,
    VendorRecord,
)


def default_server_parameters(
    python_executable: str | None = None,
) -> StdioServerParameters:
    """Parameters that launch this package's MCP server as a subprocess."""

    return StdioServerParameters(
        command=python_executable or sys.executable,
        args=["-m", "proofloop.agents.mcp.server"],
    )


def _payload(result: CallToolResult) -> Any:
    """Extract the JSON payload a tool returned.

    The server returns a JSON object as a text content block (structured content
    is not schema-declared), so we parse the first text block. An MCP error
    result is surfaced as a ``ToolError`` so the workflow's existing tool-failure
    path handles it uniformly.
    """

    if result.is_error:
        raise ToolError(f"MCP tool returned an error: {result.content}")
    if result.structured_content is not None:
        return result.structured_content
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            return json.loads(text)
    return None


class MCPToolClient:
    """A synchronous facade over one MCP ``ClientSession``.

    Use as a context manager. On enter it launches the tool server (per the
    supplied ``StdioServerParameters``), performs the MCP initialize handshake on
    a background event loop, and blocks until the session is ready. On exit it
    shuts the session and subprocess down cleanly.
    """

    def __init__(
        self,
        params: StdioServerParameters,
        *,
        ready_timeout: float = 30.0,
        call_timeout: float = 30.0,
    ) -> None:
        self._params = params
        self._ready_timeout = ready_timeout
        self._call_timeout = call_timeout
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session: ClientSession | None = None
        self._stop: asyncio.Event | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None

    # --- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "MCPToolClient":
        self._thread = threading.Thread(
            target=self._run, name="mcp-tool-client", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(self._ready_timeout):
            raise ToolError("MCP tool server did not become ready in time")
        if self._startup_error is not None:
            raise ToolError(
                f"MCP tool server failed to start: {self._startup_error!r}"
            )
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._loop is not None and self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread is not None:
            self._thread.join(timeout=self._ready_timeout)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except BaseException as error:  # noqa: BLE001 - report any startup failure
            self._startup_error = error
            self._ready.set()
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        self._stop = asyncio.Event()
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                self._ready.set()
                await self._stop.wait()

    # --- calling -----------------------------------------------------------

    def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._loop is None or self._session is None:
            raise ToolError("MCP tool client is not connected")
        future = asyncio.run_coroutine_threadsafe(
            self._acall(name, arguments), self._loop
        )
        return future.result(timeout=self._call_timeout)

    async def _acall(self, name: str, arguments: dict[str, Any]) -> Any:
        assert self._session is not None
        result = await self._session.call_tool(name, arguments)
        return _payload(result)

    def list_tool_names(self) -> list[str]:
        if self._loop is None or self._session is None:
            raise ToolError("MCP tool client is not connected")
        future = asyncio.run_coroutine_threadsafe(self._alist(), self._loop)
        return future.result(timeout=self._call_timeout)

    async def _alist(self) -> list[str]:
        assert self._session is not None
        listing = await self._session.list_tools()
        return [tool.name for tool in listing.tools]

    # --- protocol adapters (satisfy the tool_specs Protocols) --------------

    def purchase_order_tool(self) -> "_PurchaseOrderAdapter":
        return _PurchaseOrderAdapter(self)

    def vendor_tool(self) -> "_VendorAdapter":
        return _VendorAdapter(self)

    def duplicate_tool(self) -> "_DuplicateAdapter":
        return _DuplicateAdapter(self)

    def human_review_tool(self) -> "_HumanReviewAdapter":
        return _HumanReviewAdapter(self)


@dataclass
class _PurchaseOrderAdapter:
    client: MCPToolClient

    def get_purchase_order(
        self, query: PurchaseOrderQuery
    ) -> PurchaseOrderRecord | None:
        payload = self.client._call(
            "get_purchase_order", {"po_number": query.po_number}
        )
        record = (payload or {}).get("record")
        return PurchaseOrderRecord.model_validate(record) if record else None


@dataclass
class _VendorAdapter:
    client: MCPToolClient

    def get_vendor_record(self, query: VendorQuery) -> VendorRecord | None:
        payload = self.client._call(
            "get_vendor_record",
            {"vendor_id": query.vendor_id, "vendor_name": query.vendor_name},
        )
        record = (payload or {}).get("record")
        return VendorRecord.model_validate(record) if record else None


@dataclass
class _DuplicateAdapter:
    client: MCPToolClient

    def check_duplicate_invoice(
        self, query: DuplicateQuery
    ) -> DuplicateCheckResult:
        payload = self.client._call(
            "check_duplicate_invoice",
            {
                "vendor_name": query.vendor_name,
                "invoice_number": query.invoice_number,
                "total": str(query.total),
            },
        )
        return DuplicateCheckResult.model_validate(payload)


@dataclass
class _HumanReviewAdapter:
    client: MCPToolClient

    def request_human_review(
        self, request: HumanReviewRequest
    ) -> HumanReviewTicket:
        payload = self.client._call(
            "request_human_review",
            {
                "document_id": request.document_id,
                "reason": request.reason,
                "idempotency_key": request.idempotency_key,
            },
        )
        return HumanReviewTicket.model_validate(payload)
