# Arxitektura

## Prinsiplər
- Təmiz arxitektura, məsuliyyətlərin ayrılması.
- Modul kod: agentlər, servislər, ingestion ayrı.
- Yeni bazar əlavə etmək asan (yalnız kateqoriya + mənbə).

## Qatlar
```
 core/        →  kəsişən qayğılar: config, netguard (SSRF guard), ratelimit (per-IP
                 sürüşən pəncərə), security_headers, imagejunk, bgtasks, constants
 ingestion/   →  xam xəbər toplama (RSS / API / scrape) + og:image backfill
 services/    →  biznes məntiqi (dedup, store, push, link_service, watchlist_intel)
 agents/      →  AI modulları (tək məsuliyyət hər biri) + pulsuz tərcümə + llm facade
 analytics/   →  korrelyasiya, anomaliya, Power Law, analoq, radar, asset_map,
                 forecast_scorer, accuracy, SWR keş, get_quote (canlı qiymət)
 rag/         →  numpy vektor bilik bazası (knowledge.npz) + chunk / embed / store / build
 api/v1/      →  HTTP təbəqəsi (13 router qrupu — aşağıda), yalnız servisləri çağırır
 models/      →  SQLAlchemy ORM (news, news_asset link, source, category, push)
 schemas/     →  Pydantic giriş/çıxış
 scheduler    →  APScheduler (saatlıq ingestion + self-healing dövrlər)
```

### HTTP route qrupları (`api/v1/router.py`)
`/health` (+`/db`) · `/news` (list/search/{id}/content/forecast/analogs/trending/count) ·
`/chat` (+`/stream`) · `/market` (ticker/təqvimlər/brief/…) · `/push`
(key/subscribe/unsubscribe/test) · `/assets` · `/img` (news thumbnail proksisi) ·
`/anomalies` · `/correlation` (matrix/pair/explain) · `/radar` (+`/{key}`/explain/about) ·
`/analogs` · `/watchlist-intel` (mənə-aid/portfel) · `/accuracy`.

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
  klient (localStorage: watchlist / holdings / lastSeen)  ─►  şəxsi qat servisləri
     │  server HEÇ NƏ saxlamır — yalnız açarlar göndərilir      (watchlist_intel)
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
Migrasiyalar `backend/alembic/versions/`-dədir, linear zəncir, cari HEAD `f6a7b8c9d0e1`.
`app.db.base.Base` + `TimestampMixin` (`created_at`/`updated_at` server default).

| Cədvəl | Rol | Əsas sütunlar / indekslər |
|--------|-----|---------------------------|
| `categories` | Kateqoriya lookup | forex / us / crypto / commodities … |
| `sources` | Xəbər mənbələri | RSS/API mənbə metadatası |
| `news` | Mərkəzi xəbər cədvəli | başlıq + 4-dil tərcümə (`title_az/en/ru/tr`), `summary`, `content`, dedup `hash`, `published_at`, `category_id`/`source_id` FK, `impact_score`, `sentiment`, `embedding` (vektor), şəkil sahələri (`image_url`, `image_attempts`, `image_attempted_at`). İndekslər: `ix_news_published` (published DESC NULLS LAST), `ix_news_impact_published` (impact DESC, published DESC), `ix_news_image_retry` |
| `news_asset` | Xəbər ↔ aktiv bağlantı (Mənə Aid bünövrəsi) | `news_id` FK, `asset_key`, `source` (`detected`\|`forecast`), `published_at` (denormalize), forecast scoring sütunları. Keystone indeks `(asset_key, published_at DESC)` |
| `push_subscriptions` | Web push abunələri | `endpoint` (UNIQUE), `p256dh`, `auth`, `lang` |

> **Faza 4 (auth) əlavələri:** `users`, `user_identities`, `auth_sessions`,
> `password_reset_tokens`, `email_verification_tokens`, `user_*` (watchlist/holdings/
> bookmarks/alerts/saved_events/prefs), `ai_usage`, `system_flags`, və
> `push_subscriptions.user_id` — hamısı `user_id` FK ON DELETE CASCADE ilə.
