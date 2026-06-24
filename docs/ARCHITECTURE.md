# Arxitektura

## Prinsiplər
- Təmiz arxitektura, məsuliyyətlərin ayrılması.
- Modul kod: agentlər, servislər, ingestion ayrı.
- Yeni bazar əlavə etmək asan (yalnız kateqoriya + mənbə).

## Qatlar
```
 ingestion/   →  xam xəbər toplama (RSS / API / scrape) + og:image backfill
 services/    →  biznes məntiqi (dedup, store, query, push)
 agents/      →  AI modulları (tək məsuliyyət hər biri) + pulsuz tərcümə
 analytics/   →  korrelyasiya, anomaliya, Power Law, analoq, radar kəşf, SWR keş
 api/v1/      →  HTTP təbəqəsi (yalnız servisləri çağırır) + /health, /health/db
 models/      →  SQLAlchemy ORM
 schemas/     →  Pydantic giriş/çıxış
 scheduler    →  APScheduler (saatlıq ingestion + self-healing dövrlər)
```

## Planlayıcı + self-healing (APScheduler)
Saatlıq dövr və başlanğıc tutması (`startup_catchup`) hər ingestion-dan sonra:
tərcüməsiz/uğursuz xəbərləri drenaj edir (gtx retry + backoff; uğursuzluq daimi
İngiliscə kilidləmir — `title_az` NULL qalır, növbəti dövrdə retry), şəkilsiz
xəbərlərə `og:image` backfill edir, yeni embedding/anomaliya skanı işlədir.
Performans: ağır analitika SWR keş + startup prewarm ilə (endpoint-lər isti ~1ms).

## AI Agentləri (modul dizayn)
| Agent | Məsuliyyət |
|-------|------------|
| NewsCollectorAgent | Mənbələrdən xam xəbər çəkir |
| TranslationAgent | Dil aşkarla → Azərbaycancaya tərcümə |
| SummarizationAgent | Qısa xülasə yaradır |
| CategorizationAgent | Forex / US / Crypto təyin edir |
| FinancialAdvisorAgent | Chat — GPT + Claude debate |
| CorrelationAgent | Pair korrelyasiya + chart |

## AI Advisor — 2 AI debate axını
```
İstifadəçi sualı
      │
      ▼
RAG: uyğun xəbərləri DB-dən çək
      │
      ├──► GPT  → ilkin nəticə
      └──► Claude → ilkin nəticə
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
