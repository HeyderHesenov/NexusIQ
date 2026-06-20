# Arxitektura

## Prinsiplər
- Təmiz arxitektura, məsuliyyətlərin ayrılması.
- Modul kod: agentlər, servislər, ingestion ayrı.
- Yeni bazar əlavə etmək asan (yalnız kateqoriya + mənbə).

## Qatlar
```
 ingestion/   →  xam xəbər toplama (RSS / API / scrape)
 services/    →  biznes məntiqi (dedup, store, query)
 agents/      →  AI modulları (tək məsuliyyət hər biri)
 analytics/   →  korrelyasiya + chart generasiyası
 api/v1/      →  HTTP təbəqəsi (yalnız servisləri çağırır)
 models/      →  SQLAlchemy ORM
 schemas/     →  Pydantic giriş/çıxış
```

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
