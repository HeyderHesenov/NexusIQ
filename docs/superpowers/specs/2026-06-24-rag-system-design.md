# Real RAG System + Hibrid Marşrutlaşdırma — Dizayn

Tarix: 2026-06-24
Status: təsdiqlənmiş

## Məqsəd

AI Asistantı əsl vektor RAG ilə gücləndirmək. Sadə/məlumat suallarına ucuz RAG
yolu cavab versin; qrafik və xəbər müzakirələrində mövcud iki AI (iki model)
debate işləsin. Cavab müddəti maksimum 10 saniyə.

Hazırkı `advisor._rag_context` yalnız açar-söz `ILIKE` axtarışıdır — əsl RAG deyil.
Bu dizayn onu curated finans bilik bazası üzərində vektor axtarışla əvəz edir.

## Memarlıq

İki yol, model router seçir:

- **RAG yolu** (`info`): query embed → cosine top-k bilik chunk-ları → tək model
  ifadələşdirmə (seçilmiş dildə). Debate yoxdur. Sürətli, ucuz.
- **Debate yolu** (`chart`, `discussion`): mövcud iki model paralel analiz +
  sintez. İndi RAG bilik chunk-ları da kontekstə əlavə olunur.

Hər iki yol eyni NDJSON axın protokolunu saxlayır (`chart` / `delta` / `done`).
Frontend dəyişmir.

## Komponentlər

### Bilik bazası — `backend/app/rag/knowledge/`

Markdown faylları, `##` başlıqlarla chunk-lara bölünür. Müəllif: AI (curated).

- `terms.md` — finans terminləri + mənası (P/E, RSI, hedge, likvidlik, inflyasiya,
  yield curve, beta, volatillik, və s.).
- `assets.md` — hər asset sinfi nədir, onu nə hərəkət etdirir (səhm, indeks, forex,
  əmtəə, kripto).
- `impact.md` — hadisə→asset təsir qaydaları, dərəcə və səbəb (Fed rate↑ → DXY↑,
  qızıl↓; OPEC kəsinti → neft↑; CPI yüksək → indekslər↓).

### `backend/app/rag/`

- `chunk.py` — markdown faylları oxuyur, `##` başlıqlar üzrə chunk-lara bölür.
  Hər chunk: `{id, title, text, source_file}`.
- `embed.py` — AI `embedding modeli` ilə mətn embed edir (batch).
- `store.py` — `knowledge.npz` yükləyir (yaddaşda saxlanır), query üçün cosine
  similarity ilə top-k chunk qaytarır.
- `build.py` — CLI: chunk-ları embed edib `knowledge.npz`-ə yazır. Bilik
  dəyişəndə yenidən çağırılır.
- `knowledge.npz` — build artefaktı (git-ignore: vektorlar + chunk metadatası).

### `backend/app/agents/advisor.py` (dəyişdirilir)

- `_route(question) -> {"path": "info|chart|discussion", ...}` — tək model çağırışı,
  təsnif + asset/qrafik aşkarlanması.
- `_rag_answer(question, lang, chunks)` — RAG yolu üçün tək model cavabı.
- Mövcud debate axını saxlanır, RAG chunk-ları kontekstə əlavə edilir.
- Köhnə açar-söz `_rag_context` xəbər kontekstinə görə saxlanıla bilər (debate
  yolunda xəbər lazımdır), amma bilik chunk-ları əsas RAG mənbəyidir.

## Data axını

1. İstifadəçi sualı → `_route` (AI): path + asset cütü.
2. `store.search(query_embedding, k)` → top-k bilik chunk.
3. Path `info` → `_rag_answer` (tək model, chunk-lar kontekst) → axın.
4. Path `chart`/`discussion` → korrelyasiya datası (varsa) + debate (iki model) +
   sintez, chunk-lar + xəbər kontekst → axın.

## Latency büdcəsi (max 10s)

- Router AI: ~1s.
- Query embed: ~0.3s.
- Cosine axtarış: <1ms (yaddaşda).
- RAG yolu AI cavab: ~2-4s. Cəm ~5s.
- Debate yolu: iki model paralel ~4s + sintez axın ~3s. Cəm ~8s.

## Səhv idarəsi

- AI yoxdursa → mövcud imtina mesajı.
- `knowledge.npz` yoxdursa → startup-da xəbərdarlıq, RAG boş kontekstlə işləyir
  (debate yolu pozulmur).
- Embedding xətası → şübhədə debate yoluna keç (təhlükəsiz default).
- Router xətası → debate yoluna keç.

## Test

- `store` cosine retrieval unit test: məlum sual → gözlənilən chunk başlığı.
- Router təsnif testi: 3 nümunə (term, qrafik, xəbər) → düzgün path.
- `chunk` parser testi: nümunə markdown → düzgün chunk sayı/başlıqlar.
- Real backend sınağı: 3 sual, hər biri <10s, düzgün yol seçilir.

## Qaydalar (sessiya)

- Terminallarda terse, 3-7 sözlük cümlə.
- Hər addımdan sonra auto-push.
- Secret commit edilmir (.npz git-ignore, API key .env).
- Over-coding/dead code yoxdur.
- UI işi olarsa frontend-design skill (bu spec-də frontend dəyişmir).
- Hər dəyişiklik memory-ə loglanır.

## Əhatə xaricində (YAGNI)

- pgvector / xarici vektor DB.
- Xəbərlərin vektor embed-i (xəbər debate yolunda mövcud keyword kontekstlə qalır).
- Lokal embedding modeli.
- Çoxdilli ayrıca embedding (query hər dildə embed olunur, model çoxdillidir).
