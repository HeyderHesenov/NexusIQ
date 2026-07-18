# Changelog

Bütün diqqətəlayiq dəyişikliklər. Tarixlər YYYY-MM-DD.

## 2026-07 — Real autentifikasiya + təhlükəsizlik sərtləşdirmə (v4)

Demo localStorage girişi tam server-tərəfli sessiya sistemi ilə əvəzləndi. Bütün
şəxsi data artıq istifadəçiyə bağlıdır; AI istifadəsi büdcə/kill-switch altındadır.

### Autentifikasiya
- **Hibrid token** — opaque, DB-də saxlanan refresh (30 gün, rotasiya + reuse
  aşkarlanması → sessiya zəncirinin ləğvi) + qısa HS256 JWT access (10 dəq).
- **Parol** — Argon2id (`argon2-cffi`), min 12 simvol + HIBP (fail-open) yoxlaması;
  giriş kilidləmə (per-hesab backoff, Argon2-dən əvvəl 429 + Retry-After).
- **Google** — server-tərəfli ID-token doğrulaması (`aud`/`iss`/`exp`/nonce pin),
  bağlama `sub` üzrə; konfiqurasiya olunmayanda 503 (fail-closed).
- **Parol sıfırlama** — `/auth/password-reset/request|confirm` (256-bit birdəfəlik
  token, 30 dəq) + frontend `/reset` səhifəsi və "Parolu unutdun?" axını (4 dil).
- **Sessiyalar** — `/auth/sessions` (siyahı + fərdi ləğv), `/auth/logout-all`.

### Təhlükəsizlik
- **Cookie-lər** `__Host-` prefiksli, httpOnly, SameSite; **CSRF** = Origin allowlist
  + `sid`-ə bağlı HMAC double-submit (tək ASGI middleware).
- **Same-origin proksi** — frontend `/backend/*` rewrite üzərindən (build-time
  `BACKEND_INTERNAL_URL`), ona görə `allow_credentials=False` qalır.
- **AI büdcəsi** — `ai_usage` + `system_flags`: qlobal/per-user gündəlik cap + kill
  switch; AI/push/legacy route-ları `require_user` + büdcə asılılığı altında.
- **CSP daraldıldı** (connect-src `self` + GIS), prod HSTS, `trusted_proxy_hops`
  konfiqurasiyası, prod boot açılmamış secret-lərdə fail-closed.

### İnfrastruktur
- 5 auth cədvəli + per-user data cədvəlləri (4 additive migration); `test_route_policy`
  drift qoruyucusu (yeni qorunmamış route → build xətası); real Postgres test DB
  (`nexusiq_test`) avtomatik qurulur. Backend 235 test yaşıl.

## 2026-07 — Mənə Aid: şəxsi kəşfiyyat flaqmanı (v3)

Generik analitika artıq **şəxsi VƏ sübutlu**. Hesab tələb olunmur (localStorage-first;
server heç nə saxlamır). Vahid flaqman, 3 mərhələ, ortaq bünövrə üstündə.

### Bünövrə
- **`news_asset` bağlantı cədvəli** (additive migration) — keystone indeks
  `asset_key, published_at DESC`, forecast-scoring sütunları. `news`-ə heç bir ALTER yox.
- **`asset_map` normalizator** — tam ~60 aktiv reyestr üzrə xəbər→aktiv aşkarlama;
  dəqiqlik qorunması (söz-sərhədi + böyük-hərf-standalone + deny-context + ad override),
  uyğunlaşmayan simvol atılmır, səthə çıxarılır. 17 test, real başlıqlarda 0 yanlış tutma.
- **Link populyasiyası** — ingest hook (detected, deterministik) + `backfill_links` CLI +
  scheduler `_link_cycle` self-heal; hamısı `on_conflict` idempotent.

### Əlavə olundu
- **① Mənə Aid** — ana səhifə hero + `/mene-aid/[key]`: yalnız izlədiyin aktivlərə
  toxunan xəbərlərin şəxsi digesti, əhval trendi, "sən yox ikən" təzəlik nişanı.
  Login yox, AI xərci sıfır. Link seyrəkdirsə `news_for_asset` fallback.
- **③ Mənim Portfelim** — `/portfel`: mövqe (localStorage) → canlı P&L (`get_quote`),
  çəki, və bugünkü xəbərlərin pul-çəkili sıralanması (`relevance = Σ çəki · təsir`).
- **④ Doğruluq Kartı** — `/accuracy`: proqnozların açıq doğruluğu. `forecast_scorer`
  üfüq bağlananda real qiymətlə ballar (point-in-time, `analog._move_after` reuse, LLM yox);
  uğur nisbəti naiv baza ilə **delta**, `n≥20` dürüstlük qapısı; per-aktiv güvən nişanı.
- Naviqasiya: Portfel (Wallet) + Doğruluq (Target); i18n `meneAid.*`/`portfel.*`/`acc.*` (AZ/EN/RU/TR).

### İnfrastruktur
- `config.scorer_enabled` (default aktiv, pulsuz); scheduler `_score_cycle`.
- Backfill: 4130 xəbər → 2385 detected link; 167 forecast → 627 forecast link.
- Testlər: `test_asset_map` (17) + `test_accuracy` (7) — cəmi 32 backend test yaşıl.

## 2026-06 — Bazar Təqvimi & kod review

### Əlavə olundu
- **Bazar Təqvimi — ForexFactory üslubu.** `/markets` bütün tablar gün-üzrə
  qruplanmış cədvələ keçdi (sticky gün başlıqları, lokallaşdırılmış AZ/EN/RU/TR
  həftəgünü/ay adları). İqtisadi təqvimdə tarix-aralığı presetləri
  (Bugün / Bu həftə / Gələn həftə / Bu ay) + xüsusi from–to (maks 1 ay) +
  impact filtri (Yüksək/Orta) + axtarış. Sütunlar: vaxt · valyuta · təsir ·
  hadisə · Faktiki/Proqnoz/Əvvəlki. Yeni `CalendarLedger` komponenti.
- **İqtisadi təqvim mənbəyi → TradingView** (açıq endpoint, key-siz), bugündən
  ~1 ay irəli pəncərə + `actual` sahəsi; ForexFactory `thisweek` XML fallback
  kimi qalır.
- **Təsvirsiz xəbərlərə AI xülasə** (məqalə-kontekstli, self-healing).

### Düzəliş
- İqtisadi təqvimdə keçmiş günlər filtrlənir — öndə bugün + gələcək hadisələr.

### Refaktor / təmizləmə (kod review passı)
- Dublikat `briefHref` → `lib/brief.ts`; inline `Sparkline` →
  paylaşılan `components/charts/Sparkline`; dublikat `CAT_LABEL` → çoxdilli
  `news.cat.*` i18n açarları; `lib/google.ts` OAuth callback tipləndi.
- `agents/correlation_ai.py` bare-except uyğunlaşdırıldı.
- Tam arxitektura & kod review — bax `docs/ARCHITECTURE_REVIEW.md`.

### İnfrastruktur (lokal)
- `NexusFX → NexusIQ` rename-dən sonra qırılan Python venv shebang-ları
  bərpa edildi (backend `:8001` yenidən qalxdı).
