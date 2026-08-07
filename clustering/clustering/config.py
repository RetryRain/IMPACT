from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
