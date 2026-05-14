from pydantic import BaseModel


class LLMConfig(BaseModel):
    provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    llamacpp_base_url: str = "http://127.0.0.1:11435"
    llamacpp_model: str = "qwen2.5-3b-instruct-q4_k_m.gguf"


class AgentConfig(BaseModel):
    system_prompt: str = ""
    active_tool_ids: list[str] = []
    active_mcp_ids: list[str] = []
    active_knowledge_ids: list[str] = []


class LLMTestRequest(BaseModel):
    prompt: str = ""


class UnifiedConfig(BaseModel):
    # LLM
    provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    llamacpp_base_url: str = "http://127.0.0.1:11435"
    llamacpp_model: str = "qwen2.5-3b-instruct-q4_k_m.gguf"
    web_search_provider: str = "duckduckgo"
    tavily_api_key: str = ""
    # Agent
    system_prompt: str = ""
    active_tool_ids: list[str] = []
    active_mcp_ids: list[str] = []
    active_knowledge_ids: list[str] = []
