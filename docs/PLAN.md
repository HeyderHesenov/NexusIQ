# NexusIQ — İcra Planı

> Financial Intelligence System + AI Analyst Terminal.
> Bloomberg + AI Assistant + News Aggregator.

## Status legendi
- [x] Bitdi  · [~] Davam edir · [ ] Başlamayıb

---

## Addım 1 — Skelet + struktur  `[x]`
- Layihə qovluqları (backend/frontend/docs).
- README, .gitignore, GitHub repo.

## Addım 2 — DB sxema + modellər  `[x]`
- PostgreSQL qoş. ✅ (homebrew@14, port 5433)
- Cədvəllər: `news`, `categories`, `sources`. ✅
- SQLAlchemy modelləri + miqrasiya. ✅ (alembic ilk migration: initial schema)

## Addım 3 — Xəbər ingestion  `[x]`
- RSS feed kollektoru (NewsCollectorAgent).
- Public API + lazımsa scraping.
- Deduplikasiya + normalize.
- Bazaya yaz.
- Qeyd: X (Twitter) PULSUZ etibarlı deyil — atlanır. Pullu key olsa,
  sonradan "influencer feed" mənbəyi əlavə oluna bilər.

## Addım 4 — AI pipeline  `[x]`  (GPT, 4 dil)
- Dil aşkarla (TranslationAgent).
- Azərbaycancaya tərcümə.
- Qısa xülasə (SummarizationAgent).
- Tag/kateqoriya (CategorizationAgent).
- Opsional: şəkil prompt-u.

## Addım 5 — Frontend tablar + kartlar  `[x]`
- Header tablar: Forex / US / Crypto. ✅
- Hər tab filtr kimi işləyir (qarışıq yox). ✅
- Xəbər kartı: başlıq, xülasə, şəkil, tag, tarix/saat, mənbə. ✅
- Backend API: `/news`, `/news/search`, `/news/{id}` (port 8001).

## Addım 6 — Tam xəbər səhifəsi + Axtarış  `[~]`
- Karta klik → daxili `/news/[id]` səhifəsi (yeni tab), orijinala YOX. ✅
- AI xülasə bölməsi + altda orijinal mənbə linki. ✅ (AI mətni Addım 4-də dolur)
- Axtarış (⌘K) işləyir. ✅
- Qalır: AI öz sözləri ilə yazsın (Addım 4 + API key).

## Auth — email/parol + Google  `[x]`
- Login/Signup tab, email+parol formu (demo), altında "Google ilə davam et". ✅

## Addım 6.5 — Web Push bildirişlər (PWA)  `[x]`
- Service Worker (`public/sw.js`) + VAPID açarları. ✅ (pulsuz)
- İcazə → abunəni bazada saxla (`push_subscriptions`). ✅ (NotifyBell + /push API)
- Yeni xəbər yarananda `pywebpush` ilə göndər. ✅ (ingestion hook)
- PWA manifest + ikonlar (iPhone üçün PWA quraşdırma). ✅
- Komputer + Android tam; iPhone yalnız PWA quruldusa (iOS 16.4+).

## Addım 7 — AI Financial Assistant  `[x]`
- Platforma içində chat UI (sağ drawer). ✅
- RAG: bazadan xəbər çək. ✅
- Struktur cavab: qısa/orta/uzun müddət + risklər. ✅
- GPT + Claude debate (FinancialAdvisorAgent). ✅
- Finance-only guard + model gizliliyi. ✅
- Axın effekti (token-token yazılma, /chat/stream NDJSON). ✅
- İki aktiv soruşulanda inline korrelyasiya qrafiki + əlaqə izahı. ✅

## Addım 8 — Korrelyasiya + analitika  `[x]`
- CorrelationAgent. ✅ (correlation_ai — GPT izah + fallback)
- Tarixi data (Yahoo Finance). ✅ (yfinance gündəlik gəlirlər)
- Pearson korrelyasiya. ✅ (scipy + pandas, /correlation API)
- Chart + UI-də göstər. ✅ (SVG heatmap + cüt xətt qrafiki, /correlation səhifəsi)
- Çıxış: dəyər + chart + AI izah (4 dil). ✅

## Əlavə (2026-06-20)  `[x]`
- Canlı bazar lenti — real qiymətlər (yfinance, /market/ticker, 60s).
- Xəbər şəkilləri — brendli generativ thumbnail (öz şəklimiz, pulsuz).

## Addım 9 — Bonuslar  `[ ]`
- Trending (ən təsirli xəbərlər).
- Sentiment skoru.
- Market Impact Score.
- Bookmark sistemi.

## Addım 10 — Cron planlayıcı  `[ ]`
- APScheduler (saatlıq ingestion).
- Hadisə əsaslı yeniləmə.

---

## AI agentləri (modul)
`NewsCollectorAgent` · `TranslationAgent` · `SummarizationAgent`
`CategorizationAgent` · `FinancialAdvisorAgent` · `CorrelationAgent`
Opsional orkestrasiya: LangGraph.

## Texnologiya
Frontend: Next.js 14 + TailwindCSS (dark).
Backend: FastAPI + SQLAlchemy async + PostgreSQL.
AI: OpenAI + Anthropic Claude.
Analitika: pandas, yfinance, scipy, plotly.
