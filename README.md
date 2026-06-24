# NexusIQ — Financial Intelligence Platform

> Bloomberg Terminal + AI Analyst + News Aggregator.
> Maliyyə kəşfiyyat platforması.
>
> **Final layihə — 1/3** (üç final layihədən birincisi).

## Nə edir
- Maliyyə xəbərlərini toplayır (RSS / API / scraping), dedup edir.
- 4 dilə tərcümə (AZ/EN/RU/TR) + xülasə + sentiment + impact bal (pulsuz heuristik).
- Forex / US Markets / Crypto / Commodities kateqoriyalara ayırır.
- Modern dark + light UI (Next.js + Tailwind), çoxdilli, peşəkar footer/nav.
- AI Financial Advisor chat (GPT + Claude birgə), token-token axın + inline qrafiklər.
- Korrelyasiya matrisi + cüt qrafiki + AI izah (Yahoo Finance).
- Anomaliya radarı (robust z-score, σ-gauge), web push bildirişləri.
- Power Law modeli (BTC), bazar təqvimi, izləmə, siqnallar, müqayisə, asset səhifəsi.
- **Radar — kəşf rejimi**: bilinməyən small-cap fürsətlər (kripto/səhm/əmtəə),
  fürsət balı + market cap + opensource link + on-demand AI izah.

## Texnologiya
| Qat | Stack |
|-----|-------|
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS |
| Backend | Python FastAPI, SQLAlchemy 2.0 (async), Pydantic |
| Verilənlər bazası | PostgreSQL 14 (lokal) |
| AI | OpenAI API + Anthropic Claude API |
| Analitika | pandas, yfinance, scipy, httpx |
| Data mənbələri | Yahoo Finance, Binance, DefiLlama, CoinGecko |
| Planlayıcı | APScheduler (saatlıq + hadisə əsaslı) |

## Arxitektura
```
RSS/API ─► NewsCollectorAgent ─► dedup/normalize ─► PostgreSQL
                                                          │
                            ┌─────────────────────────────┤
                            ▼                              │
                   AI Pipeline (per news)                 │
          Translation / Summarization /                   │
          Categorization / Sentiment / Impact             │
                                                          ▼
Yahoo / Binance / DefiLlama / CoinGecko ─► Analytics ─► Frontend (Next.js)
   (qiymət, korrelyasiya, anomaliya,          │            │
    Power Law, Radar kəşf)                     │            ▼
                                               └──► AI Advisor Chat (GPT + Claude)
                                                    + on-demand Radar/News izah
```
Bütün ağır analitika SWR keş + startup prewarm ilə servis olunur (endpoint-lər isti ~1ms).

## Qovluq strukturu
```
NexusIQ/
├── backend/          # FastAPI + AI agentləri + analitika
│   └── app/
│       ├── core/        # config, settings
│       ├── db/          # session, base
│       ├── models/      # SQLAlchemy modelləri
│       ├── schemas/     # Pydantic sxemləri
│       ├── api/v1/      # HTTP routes
│       ├── services/    # biznes məntiqi
│       ├── agents/      # AI agentləri (modul)
│       ├── ingestion/   # RSS / scraping kollektorları
│       ├── analytics/   # korrelyasiya, anomaliya, Power Law, Radar kəşf, SWR keş
│       └── utils/
├── frontend/         # Next.js + Tailwind UI
└── docs/             # arxitektura + plan + spec sənədləri
```

## Quraşdırma
Bax: [`docs/SETUP.md`](docs/SETUP.md)

## Status — addım-addım build ✅ (10/10 tamamlandı)
- [x] Addım 1 — Layihə skeleti + struktur
- [x] Addım 2 — DB sxema + modellər
- [x] Addım 3 — RSS ingestion + dedup
- [x] Addım 4 — AI pipeline (tərcümə/xülasə/tag)
- [x] Addım 5 — Frontend tablar + xəbər kartları
- [x] Addım 6 — Tam xəbər səhifəsi
- [x] Addım 7 — AI chat bot (GPT + Claude)
- [x] Addım 8 — Korrelyasiya modulu + chartlar
- [x] Addım 9 — Bonus (sentiment, impact, bookmark)
- [x] Addım 10 — Cron planlayıcı (APScheduler, saatlıq)

## Əlavə xüsusiyyətlər (v2 — Bonus Updates)
- [x] Pulsuz tərcümə (Google gtx) — 4 dil, GPT xərci olmadan
- [x] Web Push bildirişləri — Service Worker + VAPID + NotifyBell
- [x] AI chat token-token axın (NDJSON) + inline korrelyasiya qrafikləri
- [x] Anomaliya radarı — robust z-score (qiymət+həcm), σ-gauge UI
- [x] Power Law modeli (BTC, 20 illik proyeksiya)
- [x] Bazar təqvimi, asset overview (CMC üslublu), asset detal səhifəsi
- [x] İzləmə (watchlist), qiymət siqnalları, asset müqayisəsi
- [x] **Radar — kəşf rejimi**: DefiLlama gəlir ∩ CoinGecko MC \$1–50M (kripto),
      curated tematik small-cap səhm/əmtəə (MC ≤ \$1B), fürsət balı, detal səhifəsi
- [x] Çoxdilli interfeys (AZ/EN/RU/TR) + açıq/qaranlıq tema
- [x] Peşəkar footer + ikonlu dropdown naviqasiya
- [x] Performans: SWR keş + startup prewarm (endpoint-lər isti ~1ms),
      watchlist tək-overview optimallaşması, route prewarm (keçid donması yox)
- [x] **Tarixi Analoq motoru** — embedding + kNN ilə bənzər keçmiş xəbərlər və
      onlardan sonrakı bazar hərəkəti (`/analogs`)
- [x] **Anomaliya ↔ xəbər bağlantısı** — anomaliya üçün "ehtimal olunan səbəb"
      (pulsuz, AI-siz korrelyasiya)
- [x] **RAG bilik bazası + router** — sual info-dursa RAG, chart/müzakirədirsə AI debate
- [x] AI Assistant qlobal FAB — bütün səhifələrdə
- [x] Forecast/ssenari brif səhifələri + çoxdilli AI xülasə (4 dil)
- [x] Asset registry genişlənməsi — 14 forex cütü, Binance top-50 coin
- [x] **Self-healing data pipeline** — tərcümə uğursuzluğu (gtx retry/backoff) və
      şəkilsiz xəbər (og:image backfill) avtomatik bərpa, daimi İngiliscə kilidlənmə yox
- [x] SPA daxili naviqasiya (tam reload hissi yox) + yumşaq eased collapse effektləri
- [x] Light mode isti-neytral (greige) kalibrlənmə — parıltısız, AA kontrast, dərinlik
