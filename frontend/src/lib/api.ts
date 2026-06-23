/**
 * Backend API klienti.
 * Bütün sorğular bu nöqtədən keçir — endpointlər sonrakı addımlarda artacaq.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: JSON.stringify(body),
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

/**
 * NexusIQ xəbərlərini başlıq/məzmun üzrə axtarır.
 * Backend `GET /news/search?q=` (Addım 6-da tam qoşulur).
 * Endpoint hazır olmasa boş siyahı qaytarır — UI sınmır.
 */
export async function searchNews(q: string): Promise<import("@/types").NewsItem[]> {
  const query = q.trim();
  if (!query) return [];
  try {
    return await apiGet(`/news/search?q=${encodeURIComponent(query)}`);
  } catch {
    return [];
  }
}

/** Bir xəbər üçün AI bazar proqnozu (lazy — açılışdan sonra çağırılır). */
export async function getForecast(
  id: string,
  lang: string,
): Promise<import("@/types").Forecast> {
  try {
    return await apiGet(`/news/${id}/forecast?lang=${lang}`);
  } catch {
    return { ready: false };
  }
}

const _forecastPrefetched = new Set<string>();

/**
 * Hover/fokus zamanı proqnozu öncədən isidir — server keşini doldurur ki,
 * xəbər açılanda nəticə hazır olsun. Hər (id, dil) üçün yalnız bir dəfə.
 */
export function prefetchForecast(id: string, lang: string): void {
  const k = `${id}:${lang}`;
  if (_forecastPrefetched.has(k)) return;
  _forecastPrefetched.add(k);
  void getForecast(id, lang).catch(() => _forecastPrefetched.delete(k));
}

/** Ən təsirli xəbərlər (impact score + təzəlik üzrə). */
export async function getTrending(
  category: string,
  limit = 8,
): Promise<import("@/types").NewsItem[]> {
  try {
    return await apiGet(`/news/trending?category=${category}&limit=${limit}`);
  } catch {
    return [];
  }
}

/** Kateqoriya üzrə ümumi xəbər sayı — səhifələmə üçün. */
export async function getNewsCount(category: string): Promise<number> {
  try {
    const d = await apiGet<{ total: number }>(`/news/count?category=${category}`);
    return d.total ?? 0;
  } catch {
    return 0;
  }
}

/** Orijinal xəbər mətninin seçilmiş dilə tərcüməsi (lazy, keşlənir). */
export async function getTranslatedContent(
  id: string,
  lang: string,
): Promise<{ ready: boolean; text: string }> {
  try {
    return await apiGet(`/news/${id}/content?lang=${lang}`);
  } catch {
    return { ready: false, text: "" };
  }
}

/** Crypto Fear & Greed indeksi. */
export async function getFearGreed(): Promise<import("@/types").FearGreed | null> {
  try {
    return await apiGet(`/market/feargreed`);
  } catch {
    return null;
  }
}

export interface Brief {
  ready: boolean;
  what?: string;
  scenarios?: { label: string; dir: "up" | "down" | "mixed"; text: string }[];
  pairsNote?: string;
  pairs?: { sym: string; bias: "up" | "down" | "mixed"; reason: string }[];
}

/** İstənilən təqvim elementi üçün AI analizi (nədir, ssenarilər, instrumentlər). */
export async function getBrief(
  kind: string,
  name: string,
  sym: string,
  meta: string,
  lang: string,
): Promise<Brief> {
  try {
    const qs = new URLSearchParams({ kind, name, sym, meta, lang });
    return await apiGet(`/market/brief?${qs.toString()}`);
  } catch {
    return { ready: false };
  }
}

/** Bu həftənin iqtisadi təqvimi (ForexFactory). */
export async function getCalendar(): Promise<import("@/types").CalEvent[]> {
  try {
    return await apiGet(`/market/calendar`);
  } catch {
    return [];
  }
}

/** Crypto təqvimi — sektor etiketli token unlock-ları (major/rwa/ai). */
export async function getCryptoCalendar(): Promise<
  import("@/types").CryptoUnlock[]
> {
  try {
    return await apiGet(`/market/crypto-calendar`);
  } catch {
    return [];
  }
}

/** US səhm gəlir hesabatları (hər biri `ai` etiketi ilə). */
export async function getEarnings(): Promise<import("@/types").Earning[]> {
  try {
    return await apiGet(`/market/earnings`);
  } catch {
    return [];
  }
}

/** Metal qiymətləri (Gold/Silver/Platinum/Palladium/Copper) + 14g trend. */
export async function getMetals(): Promise<import("@/types").Quote[]> {
  try {
    return await apiGet(`/market/metals`);
  } catch {
    return [];
  }
}

/** Əmtəə qiymətləri (uran, neft, qaz, taxıl və s.) + 14g trend. */
export async function getCommodities(): Promise<import("@/types").Quote[]> {
  try {
    return await apiGet(`/market/commodities`);
  } catch {
    return [];
  }
}

/** Lider coinlər təqvimi — BTC halving, XRP escrow, BNB burn, unlock-lar. */
export async function getMajorsCalendar(): Promise<
  import("@/types").MajorEvent[]
> {
  try {
    return await apiGet(`/market/majors-calendar`);
  } catch {
    return [];
  }
}

interface ChatStreamHandlers {
  onChart?: (chart: import("@/types").CorrPair) => void;
  onDelta?: (text: string) => void;
  onDone?: (refused: boolean) => void;
}

/**
 * AI cavabını axınla alır (NDJSON): əvvəl qrafik (varsa), sonra token-token mətn.
 * ChatGPT/Claude tərzi yazılma effekti üçün.
 */
export async function streamChat(
  message: string,
  lang: string,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, lang }),
  });
  if (!res.ok || !res.body) throw new Error(`API ${res.status}: /chat/stream`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      let ev: { type: string; text?: string; chart?: import("@/types").CorrPair; refused?: boolean };
      try {
        ev = JSON.parse(line);
      } catch {
        continue;
      }
      if (ev.type === "chart" && ev.chart) handlers.onChart?.(ev.chart);
      else if (ev.type === "delta" && ev.text) handlers.onDelta?.(ev.text);
      else if (ev.type === "done") handlers.onDone?.(Boolean(ev.refused));
    }
  }
}

/** Aktivlər arası Pearson korrelyasiya matrisi (heatmap). */
export async function getCorrelationMatrix(
  window: number,
): Promise<import("@/types").CorrMatrix | null> {
  try {
    return await apiGet(`/correlation/matrix?window=${window}`);
  } catch {
    return null;
  }
}

/** İki aktiv: korrelyasiya dəyəri + normallaşmış seriyalar (sürətli, AI yox). */
export async function getCorrelationPair(
  a: string,
  b: string,
  window: number,
): Promise<import("@/types").CorrPair | null> {
  try {
    const qs = new URLSearchParams({ a, b, window: String(window) });
    return await apiGet(`/correlation/pair?${qs.toString()}`);
  } catch {
    return null;
  }
}

/** Cüt üçün AI izahı (ayrıca, yavaş ola bilər — qrafiki bloklamır). */
export async function getCorrelationExplain(
  a: string,
  b: string,
  window: number,
  lang: string,
): Promise<string | null> {
  try {
    const qs = new URLSearchParams({ a, b, window: String(window), lang });
    const d = await apiGet<{ explanation: string }>(
      `/correlation/pair/explain?${qs.toString()}`,
    );
    return d.explanation ?? null;
  } catch {
    return null;
  }
}

// Overview klient keşi — markets/assets/watchlist eyni datanı paylaşır.
// SWR backend onsuz da sürətlidir; bu, təkrar şəbəkə gediş-gəlişini və paralel
// dublikat sorğuları (in-flight dedupe) aradan qaldırır → keçidlər ani olur.
let _ovCache: { ts: number; data: import("@/types").AssetOverview[] } | null = null;
let _ovInflight: Promise<import("@/types").AssetOverview[]> | null = null;
const _OV_TTL = 30_000;

/** Bütün aktivlər — qiymət + 24s dəyişim + sparkline (CMC tərzi cədvəl).
 *
 * `force=true` keşi atlayıb təzə dəyər çəkir (interval refresh üçün).
 */
export async function getAssetsOverview(
  force = false,
): Promise<import("@/types").AssetOverview[]> {
  if (!force && _ovCache && Date.now() - _ovCache.ts < _OV_TTL) {
    return _ovCache.data;
  }
  if (_ovInflight) return _ovInflight;
  _ovInflight = apiGet<import("@/types").AssetOverview[]>(`/assets/overview`)
    .then((d) => {
      _ovCache = { ts: Date.now(), data: d };
      return d;
    })
    .catch(() => _ovCache?.data ?? [])
    .finally(() => {
      _ovInflight = null;
    });
  return _ovInflight;
}

/** Cari qiymət/həcm anomaliyaları (5 dəq keş; refresh məcburi yeniləyir). */
export async function getAnomalies(
  refresh = false,
): Promise<import("@/types").Anomaly[]> {
  try {
    return await apiGet(`/anomalies${refresh ? "?refresh=true" : ""}`);
  } catch {
    return [];
  }
}

/** İzlənə bilən aktivlərin reyestri. */
export async function getAssets(): Promise<import("@/types").Asset[]> {
  try {
    return await apiGet(`/assets`);
  } catch {
    return [];
  }
}

/** Tək aktivin canlı qiyməti. */
export async function getAssetQuote(
  key: string,
): Promise<import("@/types").AssetQuote | null> {
  try {
    return await apiGet(`/assets/${key}/quote`);
  } catch {
    return null;
  }
}

export interface AssetNewsItem {
  title: string;
  url: string | null;
  source: string | null;
  publishedAt: string | null;
  image: string | null;
  summary: string | null;
}

/** Aktivə aid xəbərlər (Yahoo Finance ticker xəbərləri). */
export async function getAssetNews(key: string): Promise<AssetNewsItem[]> {
  try {
    return await apiGet(`/assets/${key}/news`);
  } catch {
    return [];
  }
}

/** Aktiv: canlı qiymət + tarixi seriya. */
export async function getAssetDetail(
  key: string,
  range = "3mo",
): Promise<import("@/types").AssetDetail | null> {
  try {
    return await apiGet(`/assets/${key}?range=${range}`);
  } catch {
    return null;
  }
}

/** Radar — kateqoriya üzrə fürsət balı ilə sıralanmış aktivlər. */
export async function getRadar(
  category: string,
): Promise<import("@/types").RadarItem[]> {
  try {
    return await apiGet(`/radar?category=${category}`);
  } catch {
    return [];
  }
}

/** Bir radar aktivinin detalı — info + açıqlama + sayt + opensource linki. */
export async function getRadarDetail(
  key: string,
): Promise<import("@/types").RadarDetail | null> {
  try {
    return await apiGet(`/radar/${key}`);
  } catch {
    return null;
  }
}

/** Bir radar aktivi haqqında ətraflı icmal — seçilmiş dildə (AI, keşli). */
export async function getRadarAbout(
  key: string,
  lang: string,
): Promise<string | null> {
  try {
    const d = await apiGet<{ ready: boolean; text: string }>(
      `/radar/${key}/about?lang=${lang}`,
    );
    return d.ready ? d.text : null;
  } catch {
    return null;
  }
}

/** Bir radar aktivi üçün on-demand AI izahı (yalnız istəklə — API qənaəti). */
export async function getRadarExplain(
  key: string,
  lang: string,
): Promise<string | null> {
  try {
    const d = await apiGet<{ ready: boolean; text: string }>(
      `/radar/${key}/explain?lang=${lang}`,
    );
    return d.ready ? d.text : null;
  } catch {
    return null;
  }
}

/** Lider coinin Power Law (güc qanunu) modeli. */
export async function getPowerLaw(
  asset = "btc",
): Promise<import("@/types").PowerLaw | null> {
  try {
    return await apiGet(`/market/powerlaw?asset=${asset}`);
  } catch {
    return null;
  }
}

/** Power Law dəstəklənən lider coinlər. */
export async function getPowerLawAssets(): Promise<
  { key: string; label: string }[]
> {
  try {
    return await apiGet(`/market/powerlaw/assets`);
  } catch {
    return [];
  }
}
