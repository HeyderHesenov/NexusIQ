# Arxitektura & Kod Review (2026-06)

`senior-architect` + `senior-backend` + `code-review` skilləri ilə bütün sayt
üzrə keçirilən gözdən keçirmənin nəticəsi. Frontend (Next.js 14) + Backend
(FastAPI) tam audit edildi; tapıntılar yerində yoxlandı (təsdiqsiz dəyişiklik yox).

## Ümumi qiymət

**Sağlam, production-hazır kod bazası.** Aydın qatlaşma, async-first backend,
xarici API-lərdə ardıcıl fallback + keş. Audit zamanı qaldırılan bir neçə bayraq
(bloklayan I/O, çatışmayan tip işarələri) **yerində yoxlanıb yanlış çıxdı** —
kod artıq düzgün idi. Real təmizləmələr aşağıdadır.

## Backend xəritəsi (`app/`)

| Qat | Modullar |
|-----|----------|
| `api/v1/routes/` | health, news, market, chat, assets, push, anomalies, correlation, radar, analog |
| `services/` | news_service (dedup+store), push_service (Web Push/VAPID) |
| `agents/` | llm, advisor (GPT⇄Claude debate), news_ai, summarize_ai, translate_free, forecast_ai, brief_ai, radar_ai, correlation_ai, process_news |
| `analytics/` | swr (keş util), market, assets, anomaly(+news), correlation, analog, radar, discovery_*, calendar, crypto_calendar, majors_calendar, earnings, feargreed, powerlaw, scoring, backfill_* |
| `ingestion/` | run, rss_collector, sources, enrich_content, enrich_images |
| `rag/` | embed, store (numpy cosine), chunk, build |
| `models/ schemas/ core/ db/` | ORM, Pydantic, config, async session |

**Güclü tərəflər:** məsuliyyət ayrımı (routes→services→analytics→ingestion);
async-safe (httpx, SQLAlchemy async, AsyncIOScheduler); `asyncio.to_thread` ilə
bloklayan I/O (yfinance) thread-ə verilir; hər xarici çağırışda try/except +
keş fallback; SWR keş ilə request-bloklamayan arxa-plan yeniləmə.

## Bu passda tətbiq olunan təmizləmələr

### Frontend
- **Dublikat `briefHref`** (`CalendarLedger` + `MarketCalendar`) → tək
  `src/lib/brief.ts`-ə çıxarıldı, hər ikisi import edir.
- **Dublikat `Sparkline`** — `MarketCalendar`-dakı inline, sərt-kodlu hex rəngli
  variant silindi; tema-rəngli + qradiyentli paylaşılan
  `components/charts/Sparkline.tsx` istifadə olunur.
- **Dublikat `CAT_LABEL`** (`NewsCard` + `news/[id]`, hardcoded İngiliscə) →
  silindi; çoxdilli `news.cat.*` i18n açarları (AZ/EN/RU/TR).
- **`any` tipi** (`lib/google.ts` OAuth callback) → konkret tip.

### Backend
- `agents/correlation_ai.py` bare `except Exception` → `# noqa: BLE001` +
  izahlı şərh (digər agentlərlə uyğunlaşdırıldı).
- **Yoxlandı, dəyişməyə ehtiyac yox:** `anomaly.py` `yf.download` artıq
  `asyncio.to_thread(_scan_sync)` ilə çağırılır (event loop bloklanmır);
  audit-də "çatışmır" deyilən 6 funksiyanın hamısının return tip işarəsi var;
  bütün `print()`-lər CLI (`__main__`/`_main`) skriptlərindədir — orada stdout
  düzgün seçimdir, logger yox.

## Gələcək təkmilləşdirmələr (struktur-riskli — bu passda icra olunmadı)

"Strukturu pozma" prinsipinə görə aşağıdakılar **tövsiyə** kimi saxlanılır;
hər biri davranış-regressiya riski daşıyır və ayrıca test tələb edir:

1. **Keş paterninin konsolidasiyası** — `calendar`, `feargreed`,
   `crypto_calendar`, `earnings`, `majors_calendar` modulları eyni manual
   `_cache/_cache_at/_TTL` paternini təkrarlayır; `analytics/swr.py`-yə köçürmək
   qlobal state-i azaldar.
2. **Böyük faylların bölünməsi** — `analytics/assets.py` (~521 sətir),
   `agents/advisor.py` (~413), `components/market/CalendarLedger.tsx` (~474).
3. **Tək asset registri** — BTC/ETH/SPX/DXY siyahıları bir neçə modulda
   təkrarlanır; tək mənbə uyğunluğu artırardı.
4. **`title_az` vs `translations`** — News modelində denormallaşma; yalnız
   `translations` JSONB saxlamaq daha təmiz olar.

## Təhlükəsizlik & sirlər
Sərt-kodlu sirr **tapılmadı** — bütün API açarları/VAPID `core.config.settings`
(`.env`) vasitəsilə. Xarici URL-lər modul sabitləridir.
