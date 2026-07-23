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
    # XFF-ə ƏLAVƏ EDƏN öz etibarlı proksilərimizin sayı (edge/nginx/CF). Next rewrite
    # HOP DEYİL (XFF-i dəyişmədən ötürür). 0 = XFF tam iqnor, socket peer. Bax clientip.py.
    trusted_proxy_hops: int = 0
    # Rate-limit store backend. "memory" = tək-proses in-memory; sonra "redis".
    ratelimit_backend: str = "memory"

    # ---- Təhlükəsizlik ----
    # Vergüllə ayrılmış Host allowlist (Host başlığı inyeksiyasına qarşı).
    # "*" = yoxlama yoxdur — lokal dev üçün defolt; publik deploy-da real domen yaz.
    trusted_hosts: str = "*"
    # HSTS YALNIZ HTTPS arxasında məna daşıyır. Lokal HTTP-də açmaq təhlükəlidir:
    # `localhost`-a yazılan HSTS bütün lokal HTTP layihələrini sındırır.
    hsts_enabled: bool = False

    # ---- Database ----
    # Default = lokal quraşdırma (pg :5433). .env yüklənməsə belə,
    # 5432-dəki YAD PostgreSQL-ə səssiz düşməsin (əvvəl bu gizli tələ idi).
    # Şəxsi istifadəçi adı deyil, generik `postgres` — hər klonlayan üçün işləsin.
    database_url: str = (
        "postgresql+asyncpg://postgres@localhost:5433/nexusiq"
    )

    # ---- AI (provayder-agnostik — dəyərlər .env-dən) ----
    llm_primary_key: str = ""
    llm_primary_model: str = ""
    llm_secondary_key: str = ""
    llm_secondary_model: str = ""
    llm_embed_model: str = ""

    # ---- Ingestion ----
    ingest_interval_minutes: int = 60

    # ---- Scheduler (Addım 10) ----
    scheduler_enabled: bool = True
    # Saatlıq ingestion + scoring + push PULSUZdur (RSS).
    # AI tərcümə (AI) XƏRC tələb edir — default söndürülü.
    scheduler_ai_process: bool = False
    scheduler_ai_batch: int = 8
    # Pulsuz maşın tərcüməsi (Google free endpoint) — xəbərləri 4 dilə
    # SADİQ tərcümə edir (AI kimi yenidən YAZMIR). Xərcsiz → default aktiv.
    # Tarixi Analoq motoru — xəbər embedding-i (embedding modeli, ucuz).
    # AI açarı lazımdır; söndürülsə motor boş nəticə qaytarır (UI sınmır).
    embed_enabled: bool = True
    embed_batch: int = 32

    # Proqnoz doğruluq motoru — forecast linklərini real qiymət hərəkəti ilə
    # qiymətləndirir (PULSUZ, LLM yox — sırf qiymət riyaziyyatı). Default aktiv.
    scorer_enabled: bool = True

    free_translate_enabled: bool = True
    # Saatlıq backfill ölçüsü. Yeni ingestion ilə ayaqlaşmaq + backlog yığılmasın
    # deyə 30. Daha yüksək Google free endpoint-i rate-limit edib ingiliscə
    # "zəhərlənmə"yə (xəta→orijinal mətn saxlanır) gətirə bilər.
    free_translate_batch: int = 30

    # ---- AI xülasə (təsvirsiz xəbərlər üçün, AI — XƏRC) ----
    # Bəzi mənbələr (məs. Yahoo) RSS-də təsvir vermir → kart boş görünür.
    # Bu xəbərlər üçün AI məqalə kontekstinə əsasən qısa, sadiq xülasə yazır.
    # Halüsinasiyanı önləmək üçün əvvəl məqalə mətni çəkilir (pulsuz), sonra AI.
    ai_summary_enabled: bool = True
    ai_summary_batch: int = 8
    # Avtomatik dövr yalnız son N günün təsvirsiz xəbərlərini emal edir (xərc nəzarəti);
    # köhnə backlog yalnız manual CLI ilə (python -m app.agents.summarize_ai).
    ai_summary_max_age_days: int = 21

    # ---- Web Push (VAPID) ----
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_subject: str = "mailto:admin@nexusiq.local"

    # ==================== Auth (Faza 4) ====================
    # Dəyərlər Addım 1-də əlavə olunur, kod addım-addım istifadə edir (indi inert).

    # ---- JWT access token (HS256) ----
    # Bir imzalayan/bir yoxlayan → HS256. PREVIOUS sıfır-downtime rotasiya üçün.
    # Prod-da JWT_SECRET ≥32 simvol olmalıdır (validate_runtime boot-u dayandırır).
    jwt_secret: str = ""
    jwt_secret_previous: str = ""
    jwt_issuer: str = "nexusiq"
    jwt_audience: str = "nexusiq"
    access_ttl_seconds: int = 600          # 10 dəq — revokasiya pəncərəsini bağlayır
    refresh_absolute_days: int = 30
    refresh_idle_days: int = 14
    rotation_grace_seconds: int = 10        # iki-tab benign race pəncərəsi (§2.4)
    sessions_valid_from_cache_ttl: int = 60  # logout-all keşi (require_user)

    # ---- Cookie ----
    # Prod: secure→__Host- prefiks + Secure. cookie_domain BOŞ qalmalıdır (__Host- tələbi).
    cookie_secure: bool = False
    cookie_domain: str = ""

    # ---- CSRF ----
    csrf_secret: str = ""   # HMAC double-submit + Google nonce üçün

    # ---- Argon2id (parol hash) ----
    # RFC 9106 ikinci profil. 2 GiB profili DEYİL — memory-hard hash DoS gücləndiricisidir.
    argon2_time_cost: int = 3
    argon2_memory_kib: int = 65536          # 64 MiB
    argon2_parallelism: int = 4

    # ---- Parol siyasəti ----
    password_min_length: int = 12
    password_max_length: int = 128
    hibp_enabled: bool = False              # breach yoxlaması — env-qapılı, fail-OPEN

    # ---- Google OAuth (ID-token axını) ----
    # aud == google_client_id yoxlaması bütün işi görən iddiadır. Boşdursa backend 503.
    google_client_id: str = ""

    # ---- Email (verify + reset) — inert, SMTP sonra ----
    email_verification_required: bool = False
    auth_dev_expose_tokens: bool = False    # SADƏCƏ dev + bu bayraq; total ATO backdoor
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "NexusIQ <no-reply@nexusiq.local>"
    smtp_tls: bool = True

    # ---- AI büdcə (Faza 4 §11) ----
    ai_daily_calls_per_user: int = 100
    ai_global_daily_calls: int = 2000
    ai_monthly_tokens_per_user: int = 500_000   # faza 2 (token accounting)

    # ---- Auth qeydiyyat/login limitləri ----
    register_per_hour_ip: int = 3
    register_per_day_ip: int = 20

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_private_key and self.vapid_public_key)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"

    @property
    def cookie_prefix(self) -> str:
        """Secure kontekstdə `__Host-` (host-only, Path=/). Lokal HTTP-də boş."""
        return "__Host-" if self.cookie_secure else ""

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id)


@lru_cache
def get_settings() -> Settings:
    """Tək instans (cache). Hər yerdə bunu çağır."""
    return Settings()


settings = get_settings()


def validate_runtime() -> list[str]:
    """Lifespan-da (import vaxtı YOX — alembic/CLI qırılmasın) çağırılır.

    Prod-da təhlükəsiz konfiqi məcbur edir; xəbərdarlıq siyahısı qaytarır (log üçün).
    Dev-də (auth secret-ləri boş ola bilər) yalnız xəbərdarlıqlar — boot dayanmır.
    """
    s = settings
    warnings: list[str] = []

    # Footgun: verify axını hələ tam deyil (verify endpoint-i/email-i yoxdur). Bayraq
    # açıq olsa, hər parol user-i `require_user`-də 403 "email_not_verified" alır və
    # təmizləmə yolu YOXDUR. Dev/prod fərqi yox — bu həmişə sınıqdır → fail-closed.
    if s.email_verification_required:
        raise RuntimeError(
            "EMAIL_VERIFICATION_REQUIRED=true, amma email-verify axını hələ yoxdur "
            "(verify endpoint-i/email-i qurulmayıb) → bütün parol user-ləri kilidlənər. "
            "Axın tamamlanana qədər bu bayraqı açma. Boot dayandırıldı."
        )

    if not s.is_dev:
        # Footgun: ENVIRONMENT=development ilə deploy = repo-məlum dev açar = auth bypass.
        # Fail-closed məhz bu dəyişənə bağlanır.
        if len(s.jwt_secret) < 32:
            raise RuntimeError(
                "Prod-da JWT_SECRET ən azı 32 simvol olmalıdır (auth imza açarı). "
                "Yarat: python -c \"import secrets;print(secrets.token_urlsafe(48))\". Boot dayandırıldı."
            )
        if not s.csrf_secret:
            raise RuntimeError("Prod-da CSRF_SECRET təyin olunmalıdır. Boot dayandırıldı.")
        if not s.cookie_secure:
            warnings.append("COOKIE_SECURE=false prod-da — cookie-lər HTTPS-siz göndərilə bilər.")

    if s.cookie_domain:
        # __Host- host-only cookie tələb edir → Domain heç vaxt təyin olunmamalıdır.
        warnings.append("COOKIE_DOMAIN boş olmalıdır (__Host- host-only cookie tələbi).")

    if s.trusted_proxy_hops < 0:
        warnings.append("TRUSTED_PROXY_HOPS mənfi ola bilməz → 0 kimi rəftar olunur.")

    return warnings
