from __future__ import annotations

import json
from functools import lru_cache
from typing import Dict, Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    api_keys: Dict[str, str] = Field(default_factory=dict, description="Map api_key -> user_id")
    embedding_provider: str = "e5"
    vector_store_backend: str = "local"
    artifact_store_backend: str = "local"
    max_optimizer_iterations: int = 5
    max_render_attempts: int = 3
    resume_per_day: int = 50
    ingest_per_day: int = 10
    render_per_hour: int = 100
    log_level: str = "INFO"
    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    llm_timeout_seconds: int = 10

    @staticmethod
    def parse_api_keys(value: Optional[str]) -> Dict[str, str]:
        if not value:
            return {}
        try:
            return json.loads(value)
        except Exception:
            return {}


@lru_cache()
def get_settings() -> Settings:
    raw = Settings()
    # handle api keys mapping via env API_KEYS JSON
    import os

    api_keys_env = os.getenv("API_KEYS")
    if api_keys_env:
        raw.api_keys = Settings.parse_api_keys(api_keys_env)
    return raw


settings = get_settings()
