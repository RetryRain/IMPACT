from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = (
        "postgresql+psycopg://bytez:bytez@localhost:5432/bytez"
    )
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    similarity_threshold: float = 0.82
    same_source_threshold: float = 0.90
    cluster_time_window_hours: int = 48
    body_char_limit: int = 800
    batch_size: int = 32
    cluster_cooldown_minutes: int = 10

    synthesis_database_url: str = (
        "postgresql+psycopg://user:pass@placeholder-host/neondb?sslmode=require"
    )
    synthesis_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-2.5-flash"
    synthesis_body_char_limit: int = 800
    synthesis_timeout_seconds: int = 120
    synthesis_concurrency: int = 3
    synthesis_log_path: str = "logs/synthesis.jsonl"

    @field_validator("database_url", "synthesis_database_url")
    @classmethod
    def strip_database_url(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "synthesis_provider",
        "deepseek_api_key",
        "deepseek_base_url",
        "deepseek_model",
        "openrouter_api_key",
        "openrouter_base_url",
        "openrouter_model",
        "synthesis_log_path",
    )
    @classmethod
    def strip_synthesis_fields(cls, value: str) -> str:
        return value.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
