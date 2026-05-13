import json
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.agent.config import get_env_defaults, get_llm_config, set_llm_config, set_agent_config
from app.core.database import get_db
from app.models.setting import SystemSetting
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.setting import AgentConfig, LLMConfig, LLMTestRequest, UnifiedConfig

router = APIRouter()

LLM_CONFIG_KEYS = [
    "provider", "ollama_base_url", "ollama_model", "ollama_embed_model",
    "deepseek_api_key", "deepseek_api_base", "deepseek_model",
    "llamacpp_base_url", "llamacpp_model",
]

AGENT_CONFIG_KEYS = ["system_prompt", "active_tool_ids", "active_mcp_ids", "active_knowledge_ids"]


async def sync_cache_from_db(db: AsyncSession):
    """Load LLM config from DB into in-memory cache."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.in_(LLM_CONFIG_KEYS))
    )
    db_settings = {row.key: row.value for row in result.scalars().all()}
    if not db_settings:
        return
    merged = dict(get_env_defaults())
    merged.update(db_settings)
    set_llm_config(merged)


async def sync_agent_cache_from_db(db: AsyncSession):
    """Load agent config from DB into in-memory cache."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.in_(AGENT_CONFIG_KEYS))
    )
    db_settings = {row.key: row.value for row in result.scalars().all()}
    if not db_settings:
        return

    import json
    config = {}
    for key in AGENT_CONFIG_KEYS:
        raw = db_settings.get(key, "")
        if key == "system_prompt":
            config[key] = raw
        elif raw:
            try:
                val = json.loads(raw)
                if isinstance(val, list):
                    config[key] = val
                else:
                    config[key] = []
            except json.JSONDecodeError:
                config[key] = []
        else:
            config[key] = []

    set_agent_config(config)


async def _upsert(db: AsyncSession, key: str, value: str):
    stmt = select(SystemSetting).where(SystemSetting.key == key)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        db.add(SystemSetting(key=key, value=value))


# --- Ollama models discovery ---

@router.get("/ollama-models")
async def list_ollama_models(
    current_user: User = Depends(require_role("admin", "lawyer")),
):
    """Fetch available models from the Ollama server, filtered to chat-capable models."""
    cfg = get_llm_config()
    base_url = cfg.get("ollama_base_url", "http://localhost:11434")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ollama 服务连接失败: {e}")

    # Filter: exclude embedding-only model families
    embedding_families = {"bert", "nomic-bert"}
    models = []
    for m in data.get("models", []):
        family = m.get("details", {}).get("family", "")
        if family in embedding_families:
            continue
        models.append({
            "name": m["name"],
            "model": m.get("model", m["name"]),
            "parameter_size": m.get("details", {}).get("parameter_size", ""),
            "quantization_level": m.get("details", {}).get("quantization_level", ""),
            "size": m.get("size", 0),
            "modified_at": m.get("modified_at", ""),
        })

    return ApiResponse(data=models)


@router.get("/ollama-embed-models")
async def list_ollama_embed_models(
    current_user: User = Depends(require_role("admin", "lawyer")),
):
    """Fetch embedding models from the Ollama server (opposite filter of above)."""
    cfg = get_llm_config()
    base_url = cfg.get("ollama_base_url", "http://localhost:11434")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ollama 服务连接失败: {e}")

    embedding_families = {"bert", "nomic-bert"}
    models = []
    for m in data.get("models", []):
        family = m.get("details", {}).get("family", "")
        if family in embedding_families:
            models.append({
                "name": m["name"],
                "model": m.get("model", m["name"]),
                "parameter_size": m.get("details", {}).get("parameter_size", ""),
                "quantization_level": m.get("details", {}).get("quantization_level", ""),
                "size": m.get("size", 0),
                "modified_at": m.get("modified_at", ""),
            })

    return ApiResponse(data=models)




# --- LLM Config (kept for backwards compat) ---

@router.get("/llm")
async def get_llm_settings(
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    await sync_cache_from_db(db)
    return ApiResponse(data=LLMConfig(**get_llm_config()))


@router.put("/llm")
async def update_llm_settings(
    body: LLMConfig,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    for key, value in data.items():
        if key in LLM_CONFIG_KEYS:
            await _upsert(db, key, str(value) if value is not None else "")
    await db.commit()
    await sync_cache_from_db(db)
    return ApiResponse(data=LLMConfig(**get_llm_config()))


# --- LLM Test (real connectivity check) ---


@router.post("/llm/test")
async def test_llm(
    body: LLMTestRequest,
    current_user: User = Depends(require_role("admin", "lawyer")),
):
    """Send a prompt to the currently configured LLM and return the real response.

    Useful for debugging LLM connectivity, measuring latency, and verifying
    the model is working before using the chat feature.
    """
    cfg = get_llm_config()
    provider = cfg.get("provider", "ollama")
    prompt = body.prompt or "请用一句话回复：你好，你是什么模型？"

    try:
        if provider == "deepseek":
            api_key = cfg.get("deepseek_api_key", "")
            if not api_key:
                return ApiResponse(code=4001, message="DeepSeek API key 未配置", data=None)

            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=cfg.get("deepseek_model", "deepseek-chat"),
                api_key=api_key,
                base_url=cfg.get("deepseek_api_base", "https://api.deepseek.com"),
                temperature=0.1,
                max_tokens=200,
            )
        elif provider == "llamacpp":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=cfg.get("llamacpp_model", "qwen2.5-3b-instruct-q4_k_m.gguf"),
                api_key="not-needed",
                base_url=cfg.get("llamacpp_base_url", "http://127.0.0.1:11435") + "/v1",
                temperature=0.1,
                max_tokens=200,
            )
        else:
            from langchain_ollama import ChatOllama

            llm = ChatOllama(
                model=cfg.get("ollama_model", "qwen2:7b-instruct"),
                base_url=cfg.get("ollama_base_url", "http://localhost:11434"),
                temperature=0.1,
                num_predict=200,
            )

        from langchain_core.messages import HumanMessage

        start = time.monotonic()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        elapsed = round(time.monotonic() - start, 3)

        return ApiResponse(data={
            "provider": provider,
            "model": llm.model if hasattr(llm, "model") else "",
            "response": response.content,
            "latency_seconds": elapsed,
        })

    except Exception as e:
        return ApiResponse(code=4001, message=f"LLM 测试失败: {e}", data=None)


# --- Agent Config (kept for backwards compat) ---

@router.get("/agent")
async def get_agent_config(
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.in_(AGENT_CONFIG_KEYS))
    )
    db_settings = {row.key: row.value for row in result.scalars().all()}
    config = AgentConfig()
    for key in AGENT_CONFIG_KEYS:
        raw = db_settings.get(key, "")
        if key == "system_prompt":
            config.system_prompt = raw
        elif raw:
            try:
                ids = json.loads(raw)
                if isinstance(ids, list):
                    if key == "active_tool_ids":
                        config.active_tool_ids = ids
                    elif key == "active_mcp_ids":
                        config.active_mcp_ids = ids
                    elif key == "active_knowledge_ids":
                        config.active_knowledge_ids = ids
            except json.JSONDecodeError:
                pass
    return ApiResponse(data=config)


@router.put("/agent")
async def update_agent_config(
    body: AgentConfig,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await _upsert(db, "system_prompt", body.system_prompt)
    await _upsert(db, "active_tool_ids", json.dumps(body.active_tool_ids, ensure_ascii=False))
    await _upsert(db, "active_mcp_ids", json.dumps(body.active_mcp_ids, ensure_ascii=False))
    await _upsert(db, "active_knowledge_ids", json.dumps(body.active_knowledge_ids, ensure_ascii=False))
    await db.commit()
    # Sync to in-memory cache
    await sync_agent_cache_from_db(db)
    return ApiResponse(data=body)


# --- Unified Config (new — one endpoint for everything) ---

@router.get("/unified")
async def get_unified_config(
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    all_keys = LLM_CONFIG_KEYS + AGENT_CONFIG_KEYS
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.in_(all_keys))
    )
    db_settings = {row.key: row.value for row in result.scalars().all()}

    config = UnifiedConfig()

    # LLM keys: DB > env defaults
    env_defaults = get_env_defaults()
    for key in LLM_CONFIG_KEYS:
        if key in db_settings:
            setattr(config, key, db_settings[key])
        else:
            setattr(config, key, env_defaults.get(key, ""))

    # Agent keys
    for key in AGENT_CONFIG_KEYS:
        raw = db_settings.get(key, "")
        if key == "system_prompt":
            config.system_prompt = raw
        elif raw:
            try:
                ids = json.loads(raw)
                if isinstance(ids, list):
                    if key == "active_tool_ids":
                        config.active_tool_ids = ids
                    elif key == "active_mcp_ids":
                        config.active_mcp_ids = ids
                    elif key == "active_knowledge_ids":
                        config.active_knowledge_ids = ids
            except json.JSONDecodeError:
                pass

    return ApiResponse(data=config)


@router.put("/unified")
async def update_unified_config(
    body: UnifiedConfig,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()

    for key, value in data.items():
        if key in LLM_CONFIG_KEYS:
            await _upsert(db, key, str(value) if value is not None else "")
        elif key == "system_prompt":
            await _upsert(db, key, value)
        elif key in ("active_tool_ids", "active_mcp_ids", "active_knowledge_ids"):
            await _upsert(db, key, json.dumps(value, ensure_ascii=False))

    await db.commit()

    # Update in-memory caches — merge DB + env defaults for LLM
    await sync_cache_from_db(db)
    await sync_agent_cache_from_db(db)

    return ApiResponse(data=body)
