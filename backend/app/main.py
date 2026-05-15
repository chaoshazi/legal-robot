"""FastAPI application entry point with MCP lifecycle management."""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
import sentry_sdk
from sqlalchemy import select

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.database import async_session
from app.models.mcp_server import MCPServer
from app.models.setting import SystemSetting

settings = get_settings()
logger = logging.getLogger(__name__)


class _JsonFormatter(logging.Formatter):
    """Log formatter that outputs JSON objects for structured log ingestion (Loki)."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "line": record.lineno,
            },
            ensure_ascii=False,
        )

_LLM_CONFIG_KEYS = [
    "provider", "ollama_base_url", "ollama_model",
    "deepseek_api_key", "deepseek_api_base", "deepseek_model",
    "tavily_api_key", "web_search_provider",
]

_AGENT_CONFIG_KEYS = ["system_prompt", "active_tool_ids", "active_mcp_ids", "active_knowledge_ids"]


async def _sync_caches():
    """Load persisted LLM + Agent config from DB into in-memory cache on startup."""
    from app.agent.config import get_env_defaults, set_llm_config, set_agent_config

    try:
        async with async_session() as db:
            # ── LLM config ──
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key.in_(_LLM_CONFIG_KEYS))
            )
            db_settings = {row.key: row.value for row in result.scalars().all()}
            if db_settings:
                merged = dict(get_env_defaults())
                merged.update(db_settings)
                set_llm_config(merged)

            # ── Agent config ──
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key.in_(_AGENT_CONFIG_KEYS))
            )
            agent_settings = {row.key: row.value for row in result.scalars().all()}
            if agent_settings:
                import json
                config = {}
                for key in _AGENT_CONFIG_KEYS:
                    raw = agent_settings.get(key, "")
                    if key == "system_prompt":
                        config[key] = raw
                    elif raw:
                        try:
                            val = json.loads(raw)
                            config[key] = val if isinstance(val, list) else []
                        except json.JSONDecodeError:
                            config[key] = []
                    else:
                        config[key] = []
                set_agent_config(config)
    except Exception as e:
        logger.warning("Config sync skipped (DB not ready?): %s", e)


async def _start_mcp():
    """Connect to all enabled MCP servers and register their tools."""
    from app.agent.mcp_client import get_mcp_manager
    from app.agent.registry import get_registry

    try:
        async with async_session() as db:
            result = await db.execute(
                select(MCPServer).where(MCPServer.enabled.is_(True))
            )
            servers = list(result.scalars().all())

        if not servers:
            logger.info("No enabled MCP servers found.")
            return

        manager = get_mcp_manager()
        registry = get_registry()
        server_tools = await manager.start_all(servers)

        for sid, tools in server_tools.items():
            if tools:
                registry.register_mcp_tools(sid, tools)
                logger.info("MCP server '%s' registered %d tool(s).", sid, len(tools))
    except Exception as e:
        logger.warning("MCP initialization skipped: %s", e)


async def _stop_mcp():
    """Disconnect all MCP servers."""
    from app.agent.mcp_client import get_mcp_manager

    try:
        manager = get_mcp_manager()
        await manager.stop_all()
        logger.info("MCP servers disconnected.")
    except Exception as e:
        logger.warning("MCP cleanup error: %s", e)


def _setup_json_logging():
    """Configure all loggers to output JSON for Loki/Promtail ingestion."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sentry_sdk").setLevel(logging.WARNING)

    # Uvicorn access log — use same JSON handler
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_json_logging()
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration()],
            environment=settings.app_env,
        )
    await _sync_caches()
    await _start_mcp()
    yield
    await _stop_mcp()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan, redirect_slashes=False)

if settings.app_env == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict to specific domain in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(v1_router, prefix="/api/v1")

# Serve uploaded files (images, audio) for chat attachments
_uploads_dir = Path(settings.upload_storage_path)
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


# Unified error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code * 10, "message": exc.detail, "data": None},
        )
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "message": "Internal server error", "data": None},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
