# Arxitektura

## Prinsiplər
- Təmiz arxitektura, məsuliyyətlərin ayrılması.
- Modul kod: agentlər, servislər, ingestion ayrı.
- Yeni bazar əlavə etmək asan (yalnız kateqoriya + mənbə).

## Qatlar
```
 core/        →  kəsişən qayğılar: config, netguard (SSRF), ratelimit, clientip,
                 security_headers, imagejunk, bgtasks, constants;
                 AUTH: auth (deps), security (Argon2), jwtsvc (HS256), cookies, csrf, budget
 ingestion/   →  xam xəbər toplama (RSS / API / scrape) + og:image backfill
 services/    →  biznes məntiqi (dedup, store, push_service, link_service, watchlist_intel);
                 AUTH: auth_service (rotasiya/reuse), user_data (per-user CRUD), google_auth, email, hibp
 agents/      →  AI modulları (tək məsuliyyət hər biri) + pulsuz tərcümə + llm facade
 analytics/   →  korrelyasiya, anomaliya, Power Law, analoq, radar, asset_map,
                 forecast_scorer, accuracy, SWR keş, get_quote (canlı qiymət)
 rag/         →  numpy vektor bilik bazası (knowledge.npz) + chunk / embed / store / build
 api/v1/      →  HTTP təbəqəsi (route qrupları — aşağıda), yalnız servisləri çağırır
 models/      →  SQLAlchemy ORM (news, news_asset, source, category, push, users,
                 user_identities, auth_sessions, user_* data, ai_usage, system_flags)
 schemas/     →  Pydantic giriş/çıxış (news, auth, me)
 scheduler    →  APScheduler (saatlıq ingestion + self-healing + təmizlik dövrləri)
```

### HTTP route qrupları (`api/v1/router.py`)
**Publik:** `/health` · `/news` (list/search/{id}/analogs/trending/count) · `/market`
(ticker/təqvimlər/…) · `/assets` · `/img` · `/anomalies` · `/correlation` (matrix/pair) ·
`/radar` (+`/{key}`) · `/accuracy` · `/auth` (register/login/refresh/logout/google/reset).
**USER (require_user, AI olanlar + ai_budget):** `/chat` · `/news/{id}/content|forecast` ·
`/market/brief` · `/radar/{key}/explain|about` · `/correlation/pair/explain` · `/analogs/search` ·
`/push/*` · `/me/*` (watchlist/holdings/bookmarks/alerts/saved/prefs + import + intel) ·
`/auth/me|logout-all|password|sessions`. Siyasət `tests/test_route_policy.py` ilə pinlənir
(yeni/təsnifsiz route → build failure).

### Şəkil alt-sistemi (hər xəbərə 100% thumbnail)
Ödənişsiz, öz-şəklimiz zəmanəti: RSS-də şəkil yoxdursa `ingestion` `og:image` backfill
edir; `core/imagejunk` aşağı-keyfiyyət/placeholder şəkilləri filtrləyir; `img_cache`
xarici şəkilləri `netguard.safe_get` ilə (SSRF-safe) çəkib keşləyir; heç nə tapılmasa
brendli generativ thumbnail arxa qat verir. `/img/news/{id}` route-u brauzerə proksiləyir
(xarici domen açılmır, CSP `img-src` daralır).

## Planlayıcı + self-healing (APScheduler)
Saatlıq dövr və başlanğıc tutması (`startup_catchup`) hər ingestion-dan sonra:
tərcüməsiz/uğursuz xəbərləri drenaj edir (gtx retry + backoff; uğursuzluq daimi
İngiliscə kilidləmir — `title_az` NULL qalır, növbəti dövrdə retry), şəkilsiz
xəbərlərə `og:image` backfill edir, yeni embedding/anomaliya skanı işlədir.
Əlavə self-healing dövrlər (hər ikisi PULSUZ, LLM yox):
- `_link_cycle` — son xəbərlərdə xəbər↔aktiv `detected` linklərini tamamlayır
  (ingest hook qaçıranları tutur; `on_conflict` idempotent).
- `_score_cycle` — üfüqü bağlanmış `forecast` linklərini real qiymət hərəkəti ilə
  ballar (`forecast_scorer`, `analog._move_after` reuse, point-in-time).
Performans: ağır analitika SWR keş + startup prewarm ilə (endpoint-lər isti ~1ms).

## AI Agentləri (modul dizayn — `agents/`)
Hər modul tək məsuliyyətlidir. `llm.py` provayder-agnostik client facade-dır
(`primary_client()`/`secondary_client()`, `lru_cache`) — model adları gizlədilib,
çağırıcılar birbaşa provayderi bilmir.

| Modul | Məsuliyyət | Xərc |
|-------|------------|------|
| `process_news` | Per-xəbər orkestrator (tərcümə → xülasə → kateqoriya axını) | — |
| `translate_free` | Dil aşkarla → 4 dilə SADİQ tərcümə (Google gtx, pulsuz) | Pulsuz |
| `summarize_ai` | Təsvirsiz xəbərlərə məqalə-kontekstli AI xülasə | AI |
| `news_ai` | Xəbər üçün AI kateqoriya / siqnal köməkçisi | AI |
| `advisor` | Chat — çoxmodelli mühakimə (debate) + RAG | AI |
| `correlation_ai` | Cüt korrelyasiya izahı (+ deterministik fallback) | AI |
| `forecast_ai` | Proqnoz / ssenari brifi (`/news/{id}/forecast`) | AI |
| `radar_ai` | Radar fürsət izahı (`/radar/{key}/explain`,`/about`) | AI |
| `brief_ai` | Bazar brifi (`/market/brief`) | AI |

Deterministik/pulsuz işlər (kateqoriya heuristikası, sentiment leksikonu, impact bal)
AI-siz `analytics/`-də hesablanır — AI yalnız yuxarıdakı xərcli yollarda çağırılır.

## AI Advisor — 2 AI debate axını
```
İstifadəçi sualı
      │
      ▼
RAG: uyğun xəbərləri DB-dən çək
      │
      ├──► Model A → ilkin nəticə
      └──► Model B → ilkin nəticə
                 │
         fikirləri müqayisə et
                 │
        ┌────────┴────────┐
   eyni fikir?         fərqli fikir?
        │                  │
   ortaq mətn         razılaşana qədər
        │              debat (N raund)
        └────────┬─────────┘
                 ▼
        İstifadəçiyə tək cavab
```

## Verilənlər axını (xəbər)
```
RSS/API → NewsCollector → normalize → dedup (hash) → store
       → TranslationAgent → SummarizationAgent → CategorizationAgent
       → (sentiment / impact) → frontend göstərir
```

## Korrelyasiya axını
```
"X vs Y" sorğusu → yfinance tarixi data → align → Pearson (scipy/pandas)
   → SVG heatmap + cüt xətt qrafiki (öz render, plotly YOX) → izah (AI) → UI
```

## Şəxsi kəşfiyyat qatı (Mənə Aid — news↔asset link)
Bünövrə **`news_asset`** cədvəlidir (keystone indeks `asset_key, published_at DESC`):
hər sətir bir xəbərin bir aktivə toxunmasıdır.
- `source="detected"` — xəbər mətnində `asset_map` ilə aşkarlandı (deterministik, AI YOX).
  Dəqiqlik qorunması: söz-sərhədi + toqquşan tickerlər üçün böyük-hərf-standalone +
  deny-context veto + ad override (`anomaly_news` presedenti). Uyğunlaşmayan simvol
  atılmır — səthə çıxarılır.
- `source="forecast"` — AI proqnozunun göstərdiyi aktivlər; istiqamət (`scored_dir`)
  **generasiya vaxtı dondurulur** (point-in-time).

```
ingest ─► asset_map.assets_in_text ─► news_asset (detected)  ─┐
get_forecast ─► asset_map.normalize_sym ─► news_asset (forecast)│
                                                                ▼
  user_* (server: watchlist / holdings / prefs.last_seen)  ─►  şəxsi qat servisləri
     │  GET /me/intel/* (require_user; mənbə DB, request gövdəsi YOX)  (watchlist_intel)
     ├─► Mənə Aid digest   (toxunan xəbərlər + əhval + "sən yox ikən")
     ├─► Portfel P&L       (get_quote canlı qiymət; relevance = Σ çəki·təsir)
     └─► Doğruluq Kartı    (accuracy: hitRate vs naiv baza → delta, n≥20 gate)
                                        ▲
        forecast_scorer (scheduler) ───┘  üfüq bağlananda real gəlirlə hit/miss
           analog._move_after (point-in-time, lookahead yox)
```
Doğruluq üçün dürüstlük qaydaları: uğur nisbəti həmişə naiv baza ("həmişə ▲") ilə
müqayisə olunur (**delta**), və slice yalnız `n≥20` olduqda göstərilir (əks halda
"toplanır"). Bu, gənc məhsulda çaşdırıcı/bəzənmiş rəqəmin qarşısını alır.

## Verilənlər bazası sxemi (PostgreSQL, alembic)
Migrasiyalar `backend/alembic/versions/`-dədir, linear zəncir, cari HEAD `d0e1f2a3b4c5`.
`app.db.base.Base` + `TimestampMixin` (`created_at`/`updated_at` server default).

**Əsas (məzmun):**

| Cədvəl | Rol | Əsas sütunlar / indekslər |
|--------|-----|---------------------------|
| `categories` | Kateqoriya lookup | forex / us / crypto / commodities … |
| `sources` | Xəbər mənbələri | RSS/API mənbə metadatası |
| `news` | Mərkəzi xəbər cədvəli | başlıq + 4-dil tərcümə (`title_az/en/ru/tr`), `summary`, `content`, dedup `hash`, `published_at`, `category_id`/`source_id` FK, `impact_score`, `sentiment`, `embedding` (vektor), şəkil sahələri. İndekslər: `ix_news_published`, `ix_news_impact_published`, `ix_news_image_retry` |
| `news_asset` | Xəbər ↔ aktiv bağlantı (Mənə Aid bünövrəsi) | `news_id` FK, `asset_key`, `source` (`detected`\|`forecast`), `published_at` (denormalize), forecast scoring. Keystone indeks `(asset_key, published_at DESC)` |
| `push_subscriptions` | Web push abunələri | `user_id` FK (NOT NULL), `endpoint` (UNIQUE), `p256dh`, `auth`, `lang` |

**Auth + per-user (hamısı `user_id` FK ON DELETE CASCADE):**

| Cədvəl | Rol | Qeyd |
|--------|-----|------|
| `users` | Hesab | UUID PK (uuid4), `email` UNIQUE + `CHECK (email=lower(email))`, `password_hash` (Argon2 PHC, Google-only-da NULL), `failed_login_count`/`locked_until` (login backoff), `sessions_valid_from` (logout-all) |
| `user_identities` | Xarici provayder | `UNIQUE(provider, provider_subject)` — bağlama `sub` üzrə (email üzrə YOX) |
| `auth_sessions` | Refresh sessiyası | `refresh_token_hash` (SHA-256, opaque), `previous_token_hash` (grace window, partial index), `expires_at`/`last_used_at`, `revoked_at`/`revoked_reason` |
| `password_reset_tokens`, `email_verification_tokens` | Tək-istifadəlik token | `token_hash` UNIQUE, `expires_at`, `used_at` |
| `user_watchlist`/`user_holdings`/`user_bookmarks`/`user_alerts`/`user_saved_events`/`user_prefs` | Per-user data | kompozit UNIQUE (idempotent upsert) + cap; holdings/alerts `NUMERIC(24,8)` + `CHECK(>0 AND <=1e12)` (NaN/±Inf öldürür) |
| `ai_usage` | AI xərc uçotu | `user_id` (NULL=planlayıcı), `route`, `weight`; gündəlik/qlobal cap aqreqatı |
| `system_flags` | Kill switch və s. | key/value; `ai_enabled` DB-də (deploy-suz söndürmə) |

## Autentifikasiya + təhlükəsizlik sərhədi

**Token — hibrid:** stateless **HS256 JWT access** (10 dəq, hot path) + **opaque, DB-saxlanan,
SHA-256 hash-lənmiş refresh** (rotasiya + reuse detection). Refresh JWT DEYİL — reuse detection
onsuz da DB oxuması tələb edir, JWT orada yalnız alg-confusion səthi əlavə edərdi və revokasiya
işləməzdi. Access decode-da `algorithms=["HS256"]` (başlıqdan YOX) + `typ=="access"` yoxlaması —
iki klassik JWT qətli. Rotasiya `FOR UPDATE` + 10s grace window (iki-tab benign race yanlış alarm
verməsin — prod-da rotasiyanın ən çox geri qaytarılma səbəbi).

**Cookie/CSRF:** brauzer → API bütün trafik **same-origin `/backend/*` rewrite** üzərindən →
CORS iştirak etmir → `allow_credentials=False` ƏBƏDİ (fail-closed tripwire). `nexusiq_at` (Lax,
httpOnly) · `nexusiq_rt` (Strict, httpOnly) · `nexusiq_csrf` (JS-oxunan). Prod-da `__Host-` prefiks
+ Secure. CSRF = **tək ASGI middleware**: Qat 1 Origin/Referer allowlist + Qat 2 HMAC double-submit
(`sid`-ə bağlı, yalnız sessiya cookie-si olanda). Heç bir route iştirak etmir → heç biri unuda bilməz.

**Parol:** Argon2id (`t=3, m=64MiB, p=4`; 2 GiB profili DEYİL = DoS gücləndirici). Per-IP limit +
`locked_until` yoxlaması Argon2-dən ƏVVƏL. HIBP breach yoxlaması (env-qapılı, fail-OPEN). Enumerasiya:
register + reset byte-identik 202 + 250ms floor; login-də kilid 429+Retry-After (qəbul edilmiş sızma).

**Google:** GIS **ID-token** axını — backend `PyJWKClient` ilə imza + `algorithms=["RS256"]` pin +
`aud==GOOGLE_CLIENT_ID` + `email_verified` + nonce yoxlayır. Bağlama `sub` üzrə (email dəyişkəndir).
Client ID-siz düymə render olunmur + backend 503 (demo yolu yox).

**AI xərc:** hər AI route `require_user` + `ai_budget(route, weight)` — admission-da per-user +
qlobal cap + DB kill switch yoxlayır, `ai_usage` yazır (`weight`: chat~4, radar~1). Planlayıcı
(user_id=NULL) qlobal cap-a sayılır. Qeydiyyat limiti əsl nəzarətdir (per-user büdcə × N hesab).

**Sərhəd serverdir.** `AuthGate` (frontend) yalnız UX; publik API route-ları dizayn gərəyi
curl-lanandır. Əsl sərhəd serverdə `require_user`-dir. İzolyasiya service qatı + `owned` dependency
(404 not 403 — enumerasiya orakulu yox) + `test_route_policy.py` drift qoruyucusu ilə mexaniki icra olunur.
