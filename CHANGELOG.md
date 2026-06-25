# Changelog

Bütün diqqətəlayiq dəyişikliklər. Tarixlər YYYY-MM-DD.

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
- **Təsvirsiz xəbərlərə AI xülasə** (GPT, məqalə-kontekstli, self-healing).

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
