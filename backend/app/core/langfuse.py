"""Lightweight LangFuse v2 integration via REST ingestion API.

LangFuse Python SDK v3+ uses OpenTelemetry which is incompatible with
LangFuse server v2 (our self-hosted version). This module posts trace
events directly to the REST ingestion endpoint instead.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.agent.config import get_llm_config

logger = logging.getLogger(__name__)

_client = None
_INIT_DONE = False


def _get_client():
    """Return a configured LangFuse REST client, or None."""
    global _client, _INIT_DONE

    if _INIT_DONE:
        return _client

    _INIT_DONE = True
    settings = get_settings()
    if not settings.langfuse_secret_key:
        return None

    host = settings.langfuse_host.rstrip("/")
    _client = _LangfuseRestClient(
        host=host,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
    )
    logger.info("LangFuse REST client initialized, host=%s", host)
    return _client


class _LangfuseRestClient:
    """Minimal LangFuse REST client using the /api/public/ingestion endpoint."""

    def __init__(self, host: str, public_key: str, secret_key: str):
        self._host = host
        self._auth = (public_key, secret_key)
        self._client = httpx.AsyncClient(timeout=10)

    async def enqueue(self, events: list[dict]) -> None:
        """Post a batch of events to the ingestion API."""
        if not events:
            return
        try:
            resp = await self._client.post(
                f"{self._host}/api/public/ingestion",
                json={"batch": events},
                auth=self._auth,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "LangFuse ingestion failed: %s %s", resp.status_code, resp.text[:200]
                )
        except Exception as e:
            logger.warning("LangFuse ingestion error: %s", e)

    async def flush(self) -> None:
        pass  # each call posts immediately

    async def shutdown(self) -> None:
        await self._client.aclose()


def _now() -> str:
    now = datetime.now(tz=timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _get_model_info() -> dict:
    """Get current model name and parameters from config."""
    try:
        cfg = get_llm_config()
        provider = cfg.get("provider", "ollama")
        model_map = {
            "deepseek": cfg.get("deepseek_model", "deepseek-chat"),
            "ollama": cfg.get("ollama_model", "qwen2:7b-instruct"),
            "llamacpp": cfg.get("llamacpp_model", "qwen2.5-3b-instruct-q4_k_m.gguf"),
        }
        model = model_map.get(provider, "unknown")
        return {"model": f"{provider}/{model}", "provider": provider}
    except Exception:
        return {"model": "unknown", "provider": "unknown"}


async def trace_agent_call(user_input: str, agent_output: str, user_id: str = "") -> str:
    """Manually post a trace to LangFuse for an agent invocation. Returns trace_id."""
    client = _get_client()
    if client is None:
        return ""

    trace_id = uuid.uuid4().hex
    gen_id = uuid.uuid4().hex
    ts = _now()
    model_info = _get_model_info()

    body: dict = {
        "id": trace_id,
        "name": "Agent Chat",
        "input": user_input,
        "output": agent_output,
        "tags": ["legalbot", model_info["provider"]],
        "metadata": {
            "model": model_info["model"],
        },
    }
    if user_id:
        body["userId"] = user_id

    events = [
        {
            "id": uuid.uuid4().hex,
            "timestamp": ts,
            "type": "trace-create",
            "body": body,
        },
        {
            "id": uuid.uuid4().hex,
            "timestamp": ts,
            "type": "generation-create",
            "body": {
                "id": gen_id,
                "traceId": trace_id,
                "name": "LLM Call",
                "startTime": ts,
                "endTime": ts,
                "model": model_info["model"],
                "modelParameters": {"temperature": 0.1},
                "input": user_input,
                "output": agent_output,
                "usage": {
                    "input": len(user_input),
                    "output": len(agent_output),
                    "total": len(user_input) + len(agent_output),
                    "unit": "CHARACTERS",
                },
            },
        },
    ]

    await client.enqueue(events)
    return trace_id


async def create_score(
    trace_id: str,
    name: str,
    value: float | int,
    data_type: str = "NUMERIC",
    comment: str | None = None,
) -> None:
    """Post a score event linked to a trace (fire-and-forget)."""
    client = _get_client()
    if client is None or not trace_id:
        return

    event = {
        "id": uuid.uuid4().hex,
        "timestamp": _now(),
        "type": "score-create",
        "body": {
            "id": uuid.uuid4().hex,
            "traceId": trace_id,
            "name": name,
            "value": value,
            "dataType": data_type,
        },
    }
    if comment:
        event["body"]["comment"] = comment

    await client.enqueue([event])
