# NexusIQ — Financial Intelligence Platform

> Bloomberg Terminal + AI Analyst + News Aggregator.
> Maliyyə kəşfiyyat platforması.
>
> **Final layihə — 1/3** (üç final layihədən birincisi).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg)
![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg)

## Nə edir
- Maliyyə xəbərlərini toplayır (RSS / API / scraping), dedup edir.
- 4 dilə tərcümə (AZ/EN/RU/TR) + xülasə + sentiment + impact bal (pulsuz heuristik).
- Forex / US Markets / Crypto / Commodities kateqoriyalara ayırır.
- Modern dark + light UI (Next.js + Tailwind), çoxdilli, peşəkar footer/nav.
- AI Financial Advisor chat (çoxmodelli mühakimə), token-token axın + inline qrafiklər.
- Korrelyasiya matrisi + cüt qrafiki + AI izah (Yahoo Finance).
- Anomaliya radarı (robust z-score, σ-gauge), web push bildirişləri.
- Power Law modeli (BTC), bazar təqvimi, izləmə, siqnallar, müqayisə, asset səhifəsi.
- **Radar — kəşf rejimi**: bilinməyən small-cap fürsətlər (kripto/səhm/əmtəə),
  fürsət balı + market cap + opensource link + on-demand AI izah.
- **Mənə Aid — şəxsi kəşfiyyat (flaqman)**: generik ağıl artıq SƏNƏ yönəlir —
  izlədiyin aktivlərə toxunan xəbərlərin şəxsi digesti, real P&L ilə portfel və
  proqnozların açıq doğruluq kartı (aşağıda).
- **Real autentifikasiya**: email/parol (Argon2id) + Google (ID-token yoxlaması),
  server-tərəf sessiya (opaque refresh rotasiyası + reuse detection), httpOnly cookie
  + CSRF, per-user büdcə ilə AI xərc qapısı + DB kill switch. Şəxsi data server-də
  saxlanır (cross-device sync).

## Mənə Aid — şəxsi kəşfiyyat (v3 flaqman)
Bütün analitika artıq **generik yox, şəxsi VƏ sübutlu**. Şəxsi vəziyyət (izləmə,
portfel, siqnallar, bookmark) real hesabla **server-tərəf** saxlanır (`/me/*`,
cross-device sync); aşkarlamanın özü isə hələ deterministik və pulsuzdur (AI xərci yox).
Bünövrə: **`news_asset` bağlantı cədvəli** + `asset_map` normalizator (tam reyestr,
dəqiqlik qorunması ilə xəbər→aktiv aşkarlama).

- **① Mənə Aid** (`/`, hero + `/mene-aid/[key]`) — yalnız izlədiyin aktivlərə
  toxunan xəbərlərin şəxsi digesti, əhval trendi, *"Sən yox ikən N xəbər toxundu"*
  təzəlik nişanı. AI xərci sıfır (deterministik aşkarlama).
- **③ Mənim Portfelim** (`/portfel`) — mövqe (aktiv + miqdar + alış qiyməti) →
  canlı P&L, çəki, və bugünkü xəbərlərin **pul-çəkili** sıralanması
  (`relevance = Σ çəki · təsir`) — "bu xəbər MƏNİM puluma nə qədər təsir edir?".
- **④ Doğruluq Kartı** (`/accuracy`) — açıq *"biz nə qədər doğru çıxdıq"*: hər
  proqnoz real qiymət hərəkəti ilə avtomatik yoxlanır (point-in-time, LLM yox),
  uğur nisbəti naiv baza ("həmişə ▲") ilə müqayisədə (**delta**), `n≥20` dürüstlük
  qapısı. Per-aktiv güvən nişanı digestə də düşür.

## Bonuslar — şəxsi alətlər (v2)
Şəxsi qatın bünövrəsi: sən tətbiqə *nəyin sənə aid olduğunu* deyirsən — v3 "Mənə Aid"
məhz bu datanın üstündə oturur. Naviqasiya yenidən quruldu (`AppNav` bütün səhifələrdə
ortaq; ana səhifə artıq yalnız xəbər, bazar vidjetləri `/markets`-ə köçdü) və işıq/qaranlıq
rejim əlavə olundu.

- **İşıq / qaranlıq rejim** — `ThemeToggle`, localStorage-da yadda saxlanır, anti-flash script.
- **İzləmə** (`/watchlist`) — izlədiyin aktivlər, canlı qiymət (60s poll), chip ilə əlavə.
- **Qiymət xəbərdarlıqları** (`/alerts`) — hədd qaydaları; `AlertWatcher` 45s-də yoxlayır,
  həddi kəsişəndə brauzer bildirişi.
- **Asset səhifəsi** (`/asset/[key]`) — qiymət başlığı, aralıq seçici, qrafik, sürətli
  xəbərdarlıq formu və bağlı xəbərlər.
- **Müqayisə** (`/compare`) — normallaşdırılmış çoxxətli qrafik + cədvəl (maks 5 aktiv).

## Texnologiya
| Qat | Stack |
|-----|-------|
| Frontend | Next.js 15 (App Router), TypeScript, TailwindCSS |
| Backend | Python 3.13 FastAPI, SQLAlchemy 2.0 (async), Pydantic |
| Verilənlər bazası | PostgreSQL (lokal, port 5433) |
| Auth | Argon2id (argon2-cffi), HS256 access + opaque DB refresh (PyJWT), Google ID-token, CSRF |
| AI | Çoxmodelli LLM (provayder-agnostik) |
| Analitika | pandas, yfinance, scipy, httpx |
| Data mənbələri | Yahoo Finance, Binance, DefiLlama, CoinGecko |
| Planlayıcı | APScheduler (saatlıq + hadisə əsaslı) |

## Arxitektura
```
RSS/API ─► NewsCollectorAgent ─► dedup/normalize ─► PostgreSQL ◄─┐
                                          │               │       │
                     ┌────────────────────┤               │  news_asset (link)
                     ▼                    │               │  asset_map aşkarlama
            AI Pipeline (per news)        │  ingest hook ─┘  (detected + forecast)
   Translation / Summarization /          │               │
   Categorization / Sentiment / Impact    │               ▼
                                          ▼         forecast_scorer (point-in-time,
Yahoo / Binance / DefiLlama / CoinGecko ─► Analytics       real qiymət ilə balla)
   (qiymət, korrelyasiya, anomaliya,        │               │
    Power Law, Radar, asset_map)            ▼               ▼
                                     Frontend (Next.js) ◄─ Şəxsi qat (server-side /me/*)
                                          │           Mənə Aid / Portfel P&L / Doğruluq Kartı
                                          └──► AI Advisor Chat (çoxmodelli)
                                               + on-demand Radar/News izah
```
Bütün ağır analitika SWR keş + startup prewarm ilə servis olunur (endpoint-lər isti ~1ms).
Brauzer API-yə **same-origin `/backend/*`** rewrite proksisi üzərindən gedir (CORS iştirak
etmir; httpOnly cookie + CSRF). Şəxsi data server-tərəf `/me/*`-da saxlanır; kəşfiyyat
`news_asset` bağlantı cədvəli + mövcud motorlardan (analog return riyaziyyatı, get_quote) hesablanır.
AI route-ları `require_user` + per-user büdcə qapısı arxasındadır; sərhəd serverdir (`AuthGate` yalnız UX).

## Qovluq strukturu
```
NexusIQ/
├── backend/          # FastAPI + AI agentləri + analitika
│   ├── app/
│   │   ├── core/       # config, auth, security(Argon2), jwtsvc, cookies, csrf, budget,
│   │   │               #   netguard (SSRF), ratelimit, clientip, security_headers, imagejunk
│   │   ├── db/         # session, base
│   │   ├── models/     # ORM (news, news_asset, source, category, push, users, auth_sessions,
│   │   │               #   user_* data, ai_usage, system_flags)
│   │   ├── schemas/    # Pydantic sxemləri (news, auth, me)
│   │   ├── api/v1/     # HTTP routes (auth, me, news, chat, market, radar, push, accuracy…)
│   │   ├── services/   # biznes məntiqi (auth_service, user_data, google_auth, email, hibp,
│   │   │               #   link_service, watchlist_intel, push_service…)
│   │   ├── agents/     # AI modulları (advisor, brief_ai, forecast_ai… + llm facade)
│   │   ├── ingestion/  # RSS / scraping kollektorları + og:image backfill
│   │   ├── analytics/  # korrelyasiya, anomaliya, Power Law, Radar, asset_map,
│   │   │               #   forecast_scorer, accuracy, SWR keş
│   │   └── rag/        # numpy vektor bilik bazası (knowledge.npz) + router
│   ├── alembic/        # DB migrasiyaları
│   └── tests/          # pytest (asyncio + monkeypatch)
├── frontend/         # Next.js + Tailwind UI
├── scripts/          # dev.sh / status.sh / stop.sh / watchdog.sh / pg_ensure.sh
└── docs/             # arxitektura + plan + spec sənədləri
```

## Quraşdırma
Bax: [`docs/SETUP.md`](docs/SETUP.md)

Tək əmrlə işə salma:
```bash
./scripts/dev.sh      # Postgres + backend (8001) + frontend (3000)
./scripts/status.sh   # sağlamlıq yoxlaması
./scripts/stop.sh     # dayandır
```

## Status
Bütün 10 əsas addım + v2 (bonuslar) + v3 (Mənə Aid flaqmanı) + v4 (real
autentifikasiya + təhlükəsizlik sərtləşdirmə) + v5 (audit log + sessiya/cihaz UI)
tamamlanıb.
Tam dəyişiklik tarixçəsi: **[CHANGELOG.md](CHANGELOG.md)**.

## Sənədlər
- [docs/SETUP.md](docs/SETUP.md) — lokal quraşdırma + yardımçı skriptlər
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — qatlar, agentlər, DB sxemi, route qrupları
- [docs/PLAN.md](docs/PLAN.md) — addım-addım build planı
- API sənədi: backend işləyəndə `http://localhost:8001/docs` (yalnız `development`)

## Test
Backend testləri işləyən Postgres tələb edir (`./scripts/dev.sh` və ya
`scripts/pg_ensure.sh`); `nexusiq_test` bazası avtomatik qurulur (`TEST_DATABASE_URL`
ilə ləğv oluna bilər).
```bash
cd backend && .venv/bin/pytest -q                 # backend testləri
cd frontend && npx tsc --noEmit && npm run build  # frontend tip + build
```

## Töhfə & təhlükəsizlik
- Töhfə qaydaları: [CONTRIBUTING.md](CONTRIBUTING.md) · Davranış: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Zəiflik bildirişi: [SECURITY.md](SECURITY.md) — **publik issue açma**, GitHub private advisory işlət.

## Lisenziya
[MIT](LICENSE) © 2026 Heyder Hesenov
