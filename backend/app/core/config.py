from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "legal-consult-bot"
    app_env: str = "development"
    app_debug: bool = False
    app_port: int = 8000

    postgres_user: str = "legalbot"
    postgres_password: str = ""
    postgres_db: str = "legalbot"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    refresh_token_expire_days: int = 30

    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "legal_docs"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    llm_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"

    llamacpp_base_url: str = "http://127.0.0.1:11435"
    llamacpp_model: str = "qwen2.5-3b-instruct-q4_k_m.gguf"

    web_search_provider: str = "duckduckgo"
    web_search_api_base: str = ""
    web_search_api_key: str = ""
    tavily_api_key: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    sentry_dsn: str = ""

    @model_validator(mode="after")
    def _validate_production_settings(self):
        if self.app_env == "production":
            missing = []
            if not self.postgres_password:
                missing.append("POSTGRES_PASSWORD")
            if not self.jwt_secret_key:
                missing.append("JWT_SECRET_KEY")
            if not self.deepseek_api_key:
                missing.append("DEEPSEEK_API_KEY")
            if missing:
                raise ValueError(
                    f"Missing required environment variables in production mode: {', '.join(missing)}"
                )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
