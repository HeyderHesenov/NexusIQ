# Arxitektura

## Prinsiplər
- Təmiz arxitektura, məsuliyyətlərin ayrılması.
- Modul kod: agentlər, servislər, ingestion ayrı.
- Yeni bazar əlavə etmək asan (yalnız kateqoriya + mənbə).

## Qatlar
```
 ingestion/   →  xam xəbər toplama (RSS / API / scrape) + og:image backfill
 services/    →  biznes məntiqi (dedup, store, push, link_service, watchlist_intel)
 agents/      →  AI modulları (tək məsuliyyət hər biri) + pulsuz tərcümə
 analytics/   →  korrelyasiya, anomaliya, Power Law, analoq, radar, asset_map,
                 forecast_scorer, accuracy, SWR keş
 api/v1/      →  HTTP təbəqəsi (yalnız servisləri çağırır) + /health, /health/db
 models/      →  SQLAlchemy ORM (news, news_asset link, source, category, push)
 schemas/     →  Pydantic giriş/çıxış
 scheduler    →  APScheduler (saatlıq ingestion + self-healing dövrlər)
```

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

## AI Agentləri (modul dizayn)
| Agent | Məsuliyyət |
|-------|------------|
| NewsCollectorAgent | Mənbələrdən xam xəbər çəkir |
| TranslationAgent | Dil aşkarla → Azərbaycancaya tərcümə |
| SummarizationAgent | Qısa xülasə yaradır |
| CategorizationAgent | Forex / US / Crypto təyin edir |
| FinancialAdvisorAgent | Chat — çoxmodelli mühakimə (debate) |
| CorrelationAgent | Pair korrelyasiya + chart |

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
"X vs Y" sorğusu → yfinance tarixi data → align → Pearson
   → plotly chart (HTML/JSON) → izah (AI) → UI
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
