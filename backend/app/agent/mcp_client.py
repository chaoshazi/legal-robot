"""MCP client manager — connects to MCP servers and wraps their tools.

Supports both ``stdio`` (subprocess) and ``sse`` (HTTP) transports.
Lifecycle managed externally (called from ``app.main.lifespan``).
"""

import json
from contextlib import AsyncExitStack
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from app.models.mcp_server import MCPServer


def _json_type_to_python(prop: dict) -> type:
    t = prop.get("type", "string")
    if t == "string":
        return str
    if t in ("integer", "number"):
        return float if t == "number" else int
    if t == "boolean":
        return bool
    if t == "array":
        return list
    return str


def _input_schema_to_pydantic(name: str, schema: dict) -> type | None:
    """Convert JSON Schema to a Pydantic model for StructuredTool args."""
    from typing import Optional

    from pydantic import BaseModel, Field, create_model

    properties = schema.get("properties", {})
    if not properties:
        return None

    required = set(schema.get("required", []))
    fields: dict[str, tuple[type, Any]] = {}

    for field_name, prop in properties.items():
        py_type = _json_type_to_python(prop)
        desc = prop.get("description", "")
        info = Field(description=desc)
        if field_name in required:
            fields[field_name] = (py_type, info)
        else:
            fields[field_name] = (Optional[py_type], info)

    return create_model(name, **fields)


def _wrap_mcp_tool(session: ClientSession, mcp_tool) -> BaseTool:
    """Wrap an MCP-discovered tool as a LangChain ``StructuredTool``."""

    schema = mcp_tool.inputSchema or {}
    args_schema = _input_schema_to_pydantic(mcp_tool.name, schema)

    async def _execute(**kwargs: Any) -> str:
        result = await session.call_tool(mcp_tool.name, kwargs)
        if getattr(result, "isError", False):
            error_text = "; ".join(
                c.text for c in result.content if getattr(c, "type", "") == "text"
            ) or str(result)
            return f"[MCP Error: {error_text}]"
        return "\n".join(
            c.text for c in result.content if getattr(c, "type", "") == "text"
        )

    return StructuredTool(
        name=mcp_tool.name,
        description=mcp_tool.description or "",
        args_schema=args_schema,
        coroutine=_execute,
    )


class MCPClientManager:
    """Manages MCP server connections and tool discovery.

    Usage::

        mgr = MCPClientManager()
        await mgr.start_all(servers)          # connect to all enabled servers
        tools = mgr.discover_tools(server_id)  # get LangChain tools for one server
        await mgr.stop_all()                   # cleanup on shutdown
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._stacks: dict[str, AsyncExitStack] = {}

    # ── Connection ───────────────────────────────────────────────────────

    async def connect(self, server: MCPServer) -> list[BaseTool]:
        """Connect to one MCP server and return its tools as LangChain tools.

        Stores the session internally so ``call_tool`` wrappers can reference
        it.  The caller must hold a reference to the ``server.id`` for later
        ``disconnect()`` or ``discover_tools()`` calls.
        """
        sid = str(server.id)
        stack = AsyncExitStack()
        self._stacks[sid] = stack

        try:
            if server.transport == "sse":
                read, write = await stack.enter_async_context(
                    sse_client(server.url)  # type: ignore[arg-type]
                )
            else:
                args_list = json.loads(server.args) if server.args else []
                params = StdioServerParameters(
                    command=server.command or "",
                    args=args_list,
                )
                read, write = await stack.enter_async_context(
                    stdio_client(params)
                )

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[sid] = session

            result = await session.list_tools()
            return [_wrap_mcp_tool(session, t) for t in result.tools]
        except Exception:
            try:
                await stack.aclose()
            except RuntimeError:
                pass
            self._stacks.pop(sid, None)
            self._sessions.pop(sid, None)
            raise

    async def disconnect(self, server_id: str) -> None:
        """Disconnect from one MCP server and clean up resources."""
        self._sessions.pop(server_id, None)
        stack = self._stacks.pop(server_id, None)
        if stack is not None:
            try:
                await stack.aclose()
            except RuntimeError:
                # stdio_client creates an anyio cancel scope tied to the
                # startup task; calling aclose from a request handler (different
                # task) raises "Attempted to exit cancel scope in a different
                # task".  The lifecycle mismatch is harmless -- the subprocess
                # will be cleaned up on next startup.
                pass

    # ── Bulk lifecycle ───────────────────────────────────────────────────

    async def start_all(self, servers: list[MCPServer]) -> dict[str, list[BaseTool]]:
        """Connect to all enabled servers.  Returns ``{server_id: [tools...]}``."""
        result: dict[str, list[BaseTool]] = {}
        for s in servers:
            if not s.enabled:
                continue
            try:
                tools = await self.connect(s)
                result[str(s.id)] = tools
            except Exception as e:
                import logging
                logging.warning("mcp_client connect failed: %s (%s)", s.name, e)
        return result

    async def stop_all(self) -> None:
        """Disconnect all servers."""
        for sid in list(self._sessions):
            await self.disconnect(sid)

    # ── Tool discovery ───────────────────────────────────────────────────

    def discover_tools(self, server_id: str) -> list[BaseTool]:
        """Re-discover tools of an already-connected server (sync, from cache).

        Returns the tools stored during connect.  To refresh, call
        ``reconnect(server)``.
        """
        session = self._sessions.get(server_id)
        if session is None:
            return []

        import asyncio

        loop = asyncio.get_running_loop()
        future = asyncio.ensure_future(session.list_tools())
        try:
            result = loop.run_until_complete(future)
        except RuntimeError:
            # already running in async context — will not block, but
            # this helper is here for external admin endpoints.
            return []

        return [_wrap_mcp_tool(session, t) for t in result.tools]


# Module-level singleton
_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager


def reset_mcp_manager() -> None:
    global _manager
    _manager = None
