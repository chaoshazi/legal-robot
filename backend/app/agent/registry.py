"""Unified tool registry — loads builtin, DB, and MCP tools.

Usage:
    registry = ToolRegistry()
    registry.load_builtin_tools()
    registry.load_db_tools(db_tool_records)
    registry.register_mcp_tools(server_name, mcp_tools)

    agent_tools = registry.get_agent_tools(
        active_tool_ids=["..."],
        active_mcp_ids=["..."],
        knowledge_enabled=True,
    )
"""

import inspect
from typing import Any

from langchain_core.tools import BaseTool

from app.agent.tools import (
    calculate,
    calculate_compensation,
    get_current_datetime,
    python_executor,
    search_knowledge_base,
    web_search,
)
from app.models.tool import Tool as ToolModel


class ToolRegistry:
    """Central registry aggregating tools from all sources.

    Tools are identified by a unique ``qualified_name``:
      - Builtin:     ``<tool_name>``
      - DB-defined:  ``db:<tool_id>``
      - MCP:         ``mcp:<server_id>:<tool_name>``

    ``get_agent_tools()`` filters by the runtime config (active IDs + flags)
    and returns the list of ``BaseTool`` the agent should bind.
    """

    def __init__(self) -> None:
        # qualified_name → BaseTool
        self._builtin: dict[str, BaseTool] = {}
        self._db: dict[str, BaseTool] = {}
        self._mcp: dict[str, BaseTool] = {}

    # ── Builtin ──────────────────────────────────────────────────────────

    def load_builtin_tools(self) -> None:
        for t in (calculate, calculate_compensation, get_current_datetime, python_executor, search_knowledge_base, web_search):
            self._builtin[t.name] = t

    # ── DB-defined tools ─────────────────────────────────────────────────

    def load_db_tools(self, records: list[ToolModel]) -> None:
        for r in records:
            if not r.enabled:
                continue
            try:
                tool = self._build_db_tool(r)
                if tool is not None:
                    self._db[f"db:{r.id}"] = tool
            except Exception as e:
                import logging
                logging.warning("tool_registry", exc_info=e)

    def _build_db_tool(self, record: ToolModel) -> BaseTool | None:
        """Dynamically import a tool by ``module:function`` reference.

        ``function_name`` format: ``module.path:function_name``.
        If no module is given the lookup falls back to ``app.agent.tools``.
        """
        from langchain_core.tools import StructuredTool

        module_path, _, func_name = record.function_name.partition(":")
        if not func_name:
            func_name = module_path
            module_path = "app.agent.tools"

        try:
            import importlib
            mod = importlib.import_module(module_path)
            fn = getattr(mod, func_name)
        except (ImportError, AttributeError):
            return None

        # Already a @tool-decorated BaseTool
        if isinstance(fn, BaseTool):
            return fn

        import inspect
        sig = inspect.signature(fn)
        return StructuredTool.from_function(
            name=record.name or func_name,
            description=record.description or fn.__doc__ or "",
            func=fn,
            args_schema=self._sig_to_schema(func_name, sig),
        )

    @staticmethod
    def _sig_to_schema(name: str, sig: inspect.Signature) -> type | None:
        from pydantic import BaseModel, Field, create_model

        fields: dict[str, tuple[type, Any]] = {}
        for p_name, p in sig.parameters.items():
            if p_name == "self":
                continue
            ann = p.annotation if p.annotation is not inspect.Parameter.empty else str
            default = ... if p.default is inspect.Parameter.empty else p.default
            fields[p_name] = (ann, ...) if default is ... else (ann, Field(default=default))
        return create_model(name, **fields) if fields else None

    # ── MCP tools ────────────────────────────────────────────────────────

    def register_mcp_tools(self, server_id: str, tools: list[BaseTool]) -> None:
        for t in tools:
            self._mcp[f"mcp:{server_id}:{t.name}"] = t

    def unregister_mcp_tools(self, server_id: str) -> None:
        prefix = f"mcp:{server_id}:"
        self._mcp = {k: v for k, v in self._mcp.items() if not k.startswith(prefix)}

    # ── Query ────────────────────────────────────────────────────────────

    def get_agent_tools(
        self,
        active_tool_ids: list[str] | None = None,
        active_mcp_ids: list[str] | None = None,
        knowledge_enabled: bool = True,
        include_kb_tool: bool = True,
    ) -> list[BaseTool]:
        """Return the tool list the agent should bind for the current turn."""
        tools: list[BaseTool] = []

        # Builtin: search_knowledge_base is included by default so the
        # agent can look up legal references on its own.  When the caller
        # has already done pre-retrieval (chat.py /ask, /stream), pass
        # include_kb_tool=False to prevent the LLM from calling the tool
        # again and risk a "检索服务暂时不可用" error.
        # Other builtin tools (web_search, calculate, etc.) are gated by
        # active_tool_ids so the user controls what the LLM can call.
        active_ids = set(active_tool_ids or [])
        for name, t in self._builtin.items():
            if name == "search_knowledge_base":
                if knowledge_enabled and include_kb_tool:
                    tools.append(t)
            elif f"builtin:{name}" in active_ids:
                tools.append(t)

        # DB tools
        if active_tool_ids:
            for tid in active_tool_ids:
                key = f"db:{tid}"
                if t := self._db.get(key):
                    tools.append(t)

        # MCP tools
        if active_mcp_ids:
            for mid in active_mcp_ids:
                prefix = f"mcp:{mid}:"
                tools.extend(t for k, t in self._mcp.items() if k.startswith(prefix))

        return tools


# Module-level singleton
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry.load_builtin_tools()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None
