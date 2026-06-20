# NexusFX — Financial Intelligence Platform

> Bloomberg Terminal + AI Analyst + News Aggregator.
> Maliyyə kəşfiyyat platforması. Lokal kurs final layihəsi.

## Nə edir
- Maliyyə xəbərlərini toplayır (RSS / API / scraping).
- Azərbaycancaya tərcümə + xülasə + tag (AI).
- Forex / US Markets / Crypto kateqoriyalara ayırır.
- Modern dark UI-də göstərir (Next.js + Tailwind).
- İçəridə AI Financial Advisor chat (GPT + Claude birgə).
- İstənilən pair üçün korrelyasiya + chart (Yahoo Finance).

## Texnologiya
| Qat | Stack |
|-----|-------|
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS |
| Backend | Python FastAPI, SQLAlchemy 2.0 (async), Pydantic |
| Verilənlər bazası | PostgreSQL 14 (lokal) |
| AI | OpenAI API + Anthropic Claude API |
| Analitika | pandas, yfinance, scipy, plotly |
| Planlayıcı | APScheduler (saatlıq + hadisə əsaslı) |

## Arxitektura (yüksək səviyyə)
```
RSS/API ─► NewsCollectorAgent ─► dedup/normalize ─► PostgreSQL
                                                        │
                          ┌─────────────────────────────┤
                          ▼                              ▼
                 AI Pipeline (per news)          Frontend (Next.js)
        Translation / Summarization /                   │
        Categorization / Sentiment                      │
                          │                              ▼
                          ▼                    AI Advisor Chat (GPT+Claude)
                     PostgreSQL  ◄──── RAG ────────────► CorrelationAgent
```

## Qovluq strukturu
```
NexusFX/
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
│       ├── analytics/   # korrelyasiya + chartlar
│       └── utils/
├── frontend/         # Next.js + Tailwind UI
└── docs/             # arxitektura sənədləri
```

## Quraşdırma
Bax: [`docs/SETUP.md`](docs/SETUP.md)

## Status — addım-addım build
- [x] Addım 1 — Layihə skeleti + struktur
- [ ] Addım 2 — DB sxema + modellər
- [ ] Addım 3 — RSS ingestion + dedup
- [ ] Addım 4 — AI pipeline (tərcümə/xülasə/tag)
- [ ] Addım 5 — Frontend tablar + xəbər kartları
- [ ] Addım 6 — Tam xəbər səhifəsi
- [ ] Addım 7 — AI chat bot (GPT + Claude)
- [ ] Addım 8 — Korrelyasiya modulu + chartlar
- [ ] Addım 9 — Bonus (sentiment, impact, bookmark)
- [ ] Addım 10 — Cron planlayıcı
