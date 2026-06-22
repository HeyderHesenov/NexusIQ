"""Mərkəzi konfiqurasiya. Bütün dəyərlər .env-dən gəlir."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "NexusIQ"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/nexusiq"
    )

    # ---- AI ----
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ---- Ingestion ----
    ingest_interval_minutes: int = 60

    # ---- Scheduler (Addım 10) ----
    scheduler_enabled: bool = True
    # Saatlıq ingestion + scoring + push PULSUZdur (RSS).
    # AI tərcümə (GPT) XƏRC tələb edir — default söndürülü.
    scheduler_ai_process: bool = False
    scheduler_ai_batch: int = 8
    # Pulsuz maşın tərcüməsi (Google free endpoint) — xəbərləri 4 dilə
    # SADİQ tərcümə edir (GPT kimi yenidən YAZMIR). Xərcsiz → default aktiv.
    free_translate_enabled: bool = True
    free_translate_batch: int = 12

    # ---- Web Push (VAPID) ----
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_subject: str = "mailto:admin@nexusiq.local"

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_private_key and self.vapid_public_key)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Tək instans (cache). Hər yerdə bunu çağır."""
    return Settings()


settings = get_settings()
