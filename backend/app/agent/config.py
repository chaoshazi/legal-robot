"""In-memory config cache.
Settings API writes here, agent reads from here — no env var changes needed at runtime.
"""

from app.core.config import get_settings

_llm_config: dict | None = None
_agent_config: dict | None = None

LLM_CONFIG_KEYS = [
    "provider", "ollama_base_url", "ollama_model", "ollama_embed_model",
    "deepseek_api_key", "deepseek_api_base", "deepseek_model",
]

AGENT_CONFIG_KEYS = ["system_prompt", "active_tool_ids", "active_mcp_ids", "active_knowledge_ids"]


def _from_env() -> dict:
    s = get_settings()
    return {
        "provider": s.llm_provider,
        "ollama_base_url": s.ollama_base_url,
        "ollama_model": s.ollama_model,
        "ollama_embed_model": s.ollama_embed_model,
        "deepseek_api_key": s.deepseek_api_key,
        "deepseek_api_base": s.deepseek_api_base,
        "deepseek_model": s.deepseek_model,
    }


def _agent_defaults() -> dict:
    return {
        "system_prompt": "",
        "active_tool_ids": [],
        "active_mcp_ids": [],
        "active_knowledge_ids": [],
    }


def get_env_defaults() -> dict:
    """Return LLM config from environment variables (uncached)."""
    return _from_env()


# --- LLM config ---


def get_llm_config() -> dict:
    global _llm_config
    if _llm_config is None:
        _llm_config = _from_env()
    return _llm_config


def set_llm_config(config: dict):
    global _llm_config
    _llm_config = config


def reset_llm_config():
    global _llm_config
    _llm_config = None


# --- Agent config ---


def get_agent_config() -> dict:
    global _agent_config
    if _agent_config is None:
        _agent_config = _agent_defaults()
    return _agent_config


def set_agent_config(config: dict):
    global _agent_config
    _agent_config = config


def reset_agent_config():
    global _agent_config
    _agent_config = None
