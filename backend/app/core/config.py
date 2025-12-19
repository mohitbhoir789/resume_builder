from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    embedding_provider: str = "e5"
    vector_store_backend: str = "local"
    artifact_store_backend: str = "local"
    max_optimizer_iterations: int = 5
    max_render_attempts: int = 3
    log_level: str = "INFO"
    llm_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    llm_timeout_seconds: int = 10


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
