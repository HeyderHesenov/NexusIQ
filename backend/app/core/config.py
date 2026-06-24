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
    # Tarixi Analoq motoru — xəbər embedding-i (text-embedding-3-small, ucuz).
    # OpenAI açarı lazımdır; söndürülsə motor boş nəticə qaytarır (UI sınmır).
    embed_enabled: bool = True
    embed_batch: int = 32

    free_translate_enabled: bool = True
    # Saatlıq backfill ölçüsü. Yeni ingestion ilə ayaqlaşmaq + backlog yığılmasın
    # deyə 30. Daha yüksək Google free endpoint-i rate-limit edib ingiliscə
    # "zəhərlənmə"yə (xəta→orijinal mətn saxlanır) gətirə bilər.
    free_translate_batch: int = 30

    # ---- AI xülasə (təsvirsiz xəbərlər üçün, GPT — XƏRC) ----
    # Bəzi mənbələr (məs. Yahoo) RSS-də təsvir vermir → kart boş görünür.
    # Bu xəbərlər üçün GPT məqalə kontekstinə əsasən qısa, sadiq xülasə yazır.
    # Halüsinasiyanı önləmək üçün əvvəl məqalə mətni çəkilir (pulsuz), sonra GPT.
    ai_summary_enabled: bool = True
    ai_summary_batch: int = 8
    # Avtomatik dövr yalnız son N günün təsvirsiz xəbərlərini emal edir (xərc nəzarəti);
    # köhnə backlog yalnız manual CLI ilə (python -m app.agents.summarize_ai).
    ai_summary_max_age_days: int = 21

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
