"""Mərkəzi konfiqurasiya. Bütün dəyərlər .env-dən gəlir."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "NexusFX"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/nexusfx"
    )

    # ---- AI ----
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ---- Advisor ----
    advisor_max_debate_rounds: int = 3
    advisor_translate_target: str = "az"

    # ---- Ingestion ----
    ingest_interval_minutes: int = 60
    ingest_user_agent: str = "NexusFX/1.0 (+local)"

    # ---- Analytics ----
    correlation_default_window_days: int = 90

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Tək instans (cache). Hər yerdə bunu çağır."""
    return Settings()


settings = get_settings()
