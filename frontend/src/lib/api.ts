/**
 * Backend API klienti.
 * Bütün sorğular bu nöqtədən keçir. Girişlər eyni-origin `/backend` proksisi
 * üzərindən gedir (Next rewrite → 127.0.0.1:8001) ki, cookie-lər və Origin
 * yoxlaması işləsin.
 */
import { getCsrfToken } from "./csrf";

// Eyni-origin proksi. Brauzer birbaşa :8001-ə getmir → cookie/CSRF/Origin düzgün.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/backend";

// Backend assa, sorğu əbədi gözləməsin — timeout-dan sonra throw edib
// UI-ya xəta state-i ver (donmuş skeleton əvəzinə).
const REQUEST_TIMEOUT_MS = 10_000;

/** Server xəta cavabını daşıyan xəta — `code` i18n mesajına map olunur. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  constructor(status: number, code: string | undefined, path: string) {
    super(`API ${status}${code ? ` (${code})` : ""}: ${path}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** Təhlükəsiz-olmayan sorğular üçün CSRF başlığı (token yoxdursa boş). */
function csrfHeaders(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { "X-CSRF-Token": token } : {};
}

/** Xəta cavabından `code`-u müdafiəli oxuyur: `{detail:{code}}` və ya `{code}`. */
async function _errorCode(res: Response): Promise<string | undefined> {
  try {
    const data = await res.clone().json();
    return data?.detail?.code ?? data?.code ?? undefined;
  } catch {
    return undefined;
  }
}

// ---- Auth itkisi siqnalı ----
// Sərt 401 (unauthenticated / session_revoked, ya da yenilənə bilməyən
// token_expired) baş verdikdə auth-context bunu tutub giriş ekranına keçir.
let _onAuthLost: (() => void) | null = null;

/** Sərt 401 hadisəsi üçün callback qeyd edir (auth-context çağırır). */
export function setOnAuthLost(fn: (() => void) | null): void {
  _onAuthLost = fn;
}

// ---- Token yeniləmə (dedup) ----
// N paralel 401 YALNIZ bir refresh tetikləsin — paylaşılan promise.
let _refreshInflight: Promise<boolean> | null = null;

/**
 * `POST /auth/refresh` — cookie-ləri fırladır. Vaxtı keçmiş access token ilə də
 * işləyir. HEÇ VAXT 401-retry məntiqindən keçmir (sonsuz döngü riski).
 * Paralel çağırışlar eyni nəticəni paylaşır (`.finally`-də təmizlənir).
 */
export function refreshOnce(): Promise<boolean> {
  if (_refreshInflight) return _refreshInflight;
  _refreshInflight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: csrfHeaders(),
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        cache: "no-store",
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      _refreshInflight = null;
    }
  })();
  return _refreshInflight;
}

// ---- Backend sağlamlıq siqnalı ----
// Fərdi funksiyalar xətanı udub boş data qaytarır (səhifə sınmasın deyə) —
// amma "server ümumiyyətlə əlçatmazdır" halı görünməz qalmamalıdır.
// Şəbəkə səviyyəsində uğursuzluq buradan qlobal bannerə ötürülür.
type BackendListener = (down: boolean) => void;
let _backendDown = false;
const _backendListeners = new Set<BackendListener>();

function _setBackendDown(down: boolean): void {
  if (_backendDown === down) return;
  _backendDown = down;
  _backendListeners.forEach((cb) => cb(down));
}

/** Backend əlçatanlıq dəyişikliklərinə abunə — dərhal cari vəziyyətlə çağırılır. */
export function onBackendStatus(cb: BackendListener): () => void {
  _backendListeners.add(cb);
  cb(_backendDown);
  return () => {
    _backendListeners.delete(cb);
  };
}

/** Banner üçün yüngül health yoxlaması — nəticəni siqnala da ötürür. */
export async function pingHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      cache: "no-store",
      credentials: "include",
      signal: AbortSignal.timeout(3_000),
    });
    _setBackendDown(!res.ok);
    return res.ok;
  } catch {
    _setBackendDown(true);
    return false;
  }
}

// Şəbəkə xətası (server ölü) ilə HTTP xətasını (server canlı, cavab xəta)
// ayırır: yalnız birincisi qlobal "down" sayılır.
async function _tracked(path: string, req: () => Promise<Response>): Promise<Response> {
  // Refresh özü ASLA retry döngüsünə düşməsin (sonsuz döngü).
  const isRefresh = path.startsWith("/auth/refresh");

  let res: Response;
  try {
    res = await req();
  } catch (e) {
    _setBackendDown(true);
    throw e;
  }
  _setBackendDown(false);
  if (res.ok) return res;

  // 401 → vaxtı keçmiş access token-i şəffaf yeniləyib sorğunu BİR DƏFƏ təkrarla.
  if (res.status === 401 && !isRefresh) {
    const code = await _errorCode(res);

    if (code === "token_expired") {
      const refreshed = await refreshOnce();
      if (refreshed) {
        let retry: Response;
        try {
          retry = await req();
        } catch (e) {
          _setBackendDown(true);
          throw e;
        }
        _setBackendDown(false);
        if (retry.ok) return retry;
        // İkinci 401 → sessiya həqiqətən itdi.
        const code2 = await _errorCode(retry);
        if (retry.status === 401) _onAuthLost?.();
        throw new ApiError(retry.status, code2, path);
      }
      // Yeniləmə alınmadı → sessiya itdi.
      _onAuthLost?.();
      throw new ApiError(401, code, path);
    }

    if (code === "unauthenticated" || code === "session_revoked") {
      _onAuthLost?.();
      throw new ApiError(401, code, path);
    }

    // Digər 401-lər (məs. invalid_credentials) — auth itkisi deyil, sadəcə ötür.
    throw new ApiError(401, code, path);
  }

  const code = await _errorCode(res);
  throw new ApiError(res.status, code, path);
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await _tracked(path, () =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      // Timeout + credentials `...init`-dən sonra — heç vaxt səssizcə üstələnməsin.
      credentials: "include",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    }),
  );
  return res.json() as Promise<T>;
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  init?: RequestInit,
): Promise<T> {
  const res = await _tracked(path, () =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: JSON.stringify(body),
      ...init,
      // Timeout + credentials `...init`-dən sonra — heç vaxt səssizcə üstələnməsin.
      credentials: "include",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      headers: {
        "Content-Type": "application/json",
        ...csrfHeaders(),
        ...(init?.headers || {}),
      },
    }),
  );
  return res.json() as Promise<T>;
}

export async function apiPut<T>(
  path: string,
  body: unknown,
  init?: RequestInit,
): Promise<T> {
  const res = await _tracked(path, () =>
    fetch(`${API_BASE}${path}`, {
      method: "PUT",
      body: JSON.stringify(body),
      ...init,
      credentials: "include",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      headers: {
        "Content-Type": "application/json",
        ...csrfHeaders(),
        ...(init?.headers || {}),
      },
    }),
  );
  return res.json() as Promise<T>;
}

export async function apiDelete<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await _tracked(path, () =>
    fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      ...init,
      credentials: "include",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      headers: {
        "Content-Type": "application/json",
        ...csrfHeaders(),
        ...(init?.headers || {}),
      },
    }),
  );
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

/**
 * "Mənə Aid" şəxsi digest — izlənən aktivlərə toxunan xəbərlər.
 * Mənbə serverdədir: istifadəçinin saxlanmış watchlist-i + prefs.lastSeen oxunur
 * (gövdə göndərilmir). Xəta olsa boş (hazır=false) qaytarır — ana səhifə sınmır.
 */
export async function getWatchlistIntel(): Promise<import("@/types").WatchlistIntel> {
  try {
    return await apiGet(`/me/intel/watchlist`);
  } catch {
    return { ready: false, sinceCount: 0, assets: [] };
  }
}

/** Tək aktivin digesti (/mene-aid drill-down səhifəsi). Mənbə = serverdəki watchlist. */
export async function getAssetIntel(
  key: string,
): Promise<import("@/types").AssetDigest | null> {
  try {
    return await apiGet(`/me/intel/asset/${encodeURIComponent(key)}`);
  } catch {
    return null;
  }
}

/** Portfel P&L + pul-çəkili xəbər. Mənbə = serverdə saxlanan holdings + prefs.lastSeen. */
export async function getPortfolioIntel(): Promise<import("@/types").PortfolioIntel> {
  try {
    return await apiGet(`/me/intel/portfolio`);
  } catch {
    return {
      ready: false,
      totals: { value: 0, cost: 0, pnl: null, pnlPct: null },
      positions: [],
      news: [],
    };
  }
}

/** Proqnoz doğruluq kartı — açıq "biz nə qədər doğru çıxdıq" (trust layer). */
export async function getAccuracy(
  by: string,
  horizon: number,
): Promise<import("@/types").AccuracyCard> {
  try {
    return await apiGet(`/accuracy?by=${by}&horizon=${horizon}`);
  } catch {
    return { ready: false, by, horizon, slices: [] };
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

/** Bir xəbər üçün Tarixi Analoqlar (lazy — başlıqlar seçilmiş dildə). */
export async function getNewsAnalogs(
  id: string,
  lang: string,
  k = 5,
): Promise<import("@/types").AnalogResult> {
  try {
    return await apiGet(`/news/${id}/analogs?k=${k}&lang=${lang}`);
  } catch {
    return { ready: false };
  }
}

/** Azad-mətn sorğusu üçün analoqlar (/analogs kəşf səhifəsi). */
export async function searchAnalogs(
  q: string,
  lang: string,
  category = "",
  k = 5,
): Promise<import("@/types").AnalogResult> {
  const query = q.trim();
  if (!query) return { ready: false };
  try {
    const qs = new URLSearchParams({ q: query, category, k: String(k), lang });
    return await apiGet(`/analogs/search?${qs}`);
  } catch {
    return { ready: false };
  }
}

const _analogPrefetched = new Set<string>();

/** Hover/fokus zamanı analoqları öncədən isidir (kNN indeks + qiymət keşi). */
export function prefetchNewsAnalogs(id: string, lang: string): void {
  const key = `${id}:${lang}`;
  if (_analogPrefetched.has(key)) return;
  _analogPrefetched.add(key);
  void getNewsAnalogs(id, lang).catch(() => _analogPrefetched.delete(key));
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

/** Ən təsirli xəbərlər — bütün kateqoriyalar (analoq səhifəsi üçün). */
export async function getTopImpact(
  limit = 6,
): Promise<import("@/types").NewsItem[]> {
  try {
    return await apiGet(`/news/trending?limit=${limit}`);
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

/** Bütün kateqoriyalar üzrə ümumi xəbər sayı (login stat-ı üçün). */
export async function getTotalNewsCount(): Promise<number> {
  try {
    const d = await apiGet<{ total: number }>(`/news/count`);
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

export interface ChatHistoryTurn {
  role: "user" | "assistant";
  content: string;
}

interface ChatStreamHandlers {
  onChart?: (chart: import("@/types").CorrPair) => void;
  onQuote?: (quotes: import("@/types").ChatQuote[]) => void;
  onAnomalies?: (anomalies: import("@/types").ChatAnomaly[], asof: string) => void;
  onPortfolio?: (portfolio: import("@/types").ChatPortfolio) => void;
  onDelta?: (text: string) => void;
  onDone?: (refused: boolean) => void;
}

/**
 * AI cavabını axınla alır (NDJSON): əvvəl grounded kartlar (qrafik/qiymət/anomali/
 * portfel — varsa), sonra token-token mətn. AI chat tərzi yazılma effekti üçün.
 * `history` — çoxaddımlı yaddaş (follow-up konteksti üçün son növbələr).
 */
export async function streamChat(
  message: string,
  lang: string,
  handlers: ChatStreamHandlers,
  history: ChatHistoryTurn[] = [],
): Promise<void> {
  // `_tracked`-i atlayır → credentials + CSRF + 401→refresh→retry-once əl ilə.
  const doFetch = () =>
    fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...csrfHeaders() },
      body: JSON.stringify({ message, lang, history }),
    });

  let res = await doFetch();
  if (res.status === 401) {
    const code = await _errorCode(res);
    if (code === "token_expired") {
      if (await refreshOnce()) {
        res = await doFetch();
        if (res.status === 401) _onAuthLost?.();
      } else {
        _onAuthLost?.();
      }
    } else if (code === "unauthenticated" || code === "session_revoked") {
      _onAuthLost?.();
    }
  }
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
      let ev: {
        type: string;
        text?: string;
        chart?: import("@/types").CorrPair;
        quotes?: import("@/types").ChatQuote[];
        anomalies?: import("@/types").ChatAnomaly[];
        asof?: string;
        portfolio?: import("@/types").ChatPortfolio;
        refused?: boolean;
      };
      try {
        ev = JSON.parse(line);
      } catch {
        continue;
      }
      if (ev.type === "chart" && ev.chart) handlers.onChart?.(ev.chart);
      else if (ev.type === "quote" && ev.quotes) handlers.onQuote?.(ev.quotes);
      else if (ev.type === "anomalies" && ev.anomalies)
        handlers.onAnomalies?.(ev.anomalies, ev.asof || "");
      else if (ev.type === "portfolio" && ev.portfolio)
        handlers.onPortfolio?.(ev.portfolio);
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
// Anomaliya client-keşi — səhifə açılışı dərhal göstərsin (skeleton yanıb-sönməsin).
type AnomalyScan = import("@/types").AnomalyScan;
const _emptyScan = (): AnomalyScan => ({
  asof: "",
  anomalies: [],
  near: [],
  stats: { universe: 0, anomalies: 0, near: 0 },
});
let _anomCache: { ts: number; data: AnomalyScan } | null = null;
let _anomInflight: Promise<AnomalyScan> | null = null;
const _ANOM_TTL = 60_000;

export async function getAnomalies(refresh = false): Promise<AnomalyScan> {
  if (!refresh && _anomCache && Date.now() - _anomCache.ts < _ANOM_TTL) {
    return _anomCache.data;
  }
  if (!refresh && _anomInflight) return _anomInflight;
  const run = (async () => {
    try {
      const d = await apiGet<AnomalyScan>(
        `/anomalies${refresh ? "?refresh=true" : ""}`,
      );
      _anomCache = { ts: Date.now(), data: d };
      return d;
    } catch {
      return _anomCache?.data ?? _emptyScan();
    } finally {
      _anomInflight = null;
    }
  })();
  if (!refresh) _anomInflight = run;
  return run;
}

/** Naviqasiya hover-i — anomaliya datasını qabaqcadan çək. */
export function prefetchAnomalies(): void {
  if (_anomCache && Date.now() - _anomCache.ts < _ANOM_TTL) return;
  void getAnomalies(false);
}

/** Anomaliyanın ehtimal səbəbi — aktivi qeyd edən son xəbərlər (pulsuz, lazy). */
export async function getAnomalyNews(
  key: string,
  k = 3,
): Promise<import("@/types").NewsItem[]> {
  try {
    return await apiGet(`/anomalies/${key}/news?k=${k}`);
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

/**
 * Xəbər örtüyünün proksi URL-i — naşirin tam ölçülü şəklini (ölçdük: 96×64
 * qutuya 216 KB) kart eninə kiçildilmiş WebP kimi verir (4.8 KB) və eyni-origin
 * olduğu üçün HTTP/2 üzərindən multipleks olunur. `w` backend-də ağ siyahıdadır.
 */
export function newsImageUrl(newsId: string, w: number): string {
  return `${API_BASE}/img/news/${newsId}?w=${w}`;
}

export interface AssetNewsItem {
  /** DB xəbəri → daxili `/news/{id}` linki; Yahoo ehtiyat xəbəri → null (xarici link). */
  id: string | null;
  title: string;
  url: string | null;
  source: string | null;
  publishedAt: string | null;
  imageUrl: string | null;
  category: import("@/types").Category;
  summary: string | null;
}

/** Aktivə aid xəbərlər — DB-first (news_asset), boşluqda Yahoo ehtiyatı. */
export async function getAssetNews(
  key: string,
  limit = 8,
): Promise<AssetNewsItem[]> {
  try {
    return await apiGet(`/assets/${key}/news?limit=${limit}`);
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

const _radarDetailCache = new Map<string, import("@/types").RadarDetail>();
const _radarPrefetching = new Set<string>();

/** Bir radar aktivinin detalı — info + açıqlama + sayt + opensource linki.
 * Nəticə client-də keşlənir ki, hover-prefetch-dən sonra açılış ani olsun. */
export async function getRadarDetail(
  key: string,
): Promise<import("@/types").RadarDetail | null> {
  const cached = _radarDetailCache.get(key);
  if (cached) return cached;
  try {
    const d = await apiGet<import("@/types").RadarDetail>(`/radar/${key}`);
    _radarDetailCache.set(key, d);
    return d;
  } catch {
    return null;
  }
}

/** Hover/fokus zamanı detalı öncədən çəkib keşləyir — klik anında skeleton yox. */
export function prefetchRadarDetail(key: string): void {
  if (_radarDetailCache.has(key) || _radarPrefetching.has(key)) return;
  _radarPrefetching.add(key);
  void getRadarDetail(key).finally(() => _radarPrefetching.delete(key));
}

/** Radar aktivi haqqında icmalı seçilmiş dildə token-token axıdır (keşli).
 * Hər parça gələndə `onDelta` çağırılır → mətn tədricən görünür, gözləmə azalır. */
export async function streamRadarAbout(
  key: string,
  lang: string,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  try {
    // `_tracked`-i atlayır → credentials + 401→refresh→retry-once əl ilə.
    const doFetch = () =>
      fetch(`${API_BASE}/radar/${key}/about?lang=${lang}`, {
        cache: "no-store",
        credentials: "include",
        signal,
      });

    let res = await doFetch();
    if (res.status === 401) {
      const code = await _errorCode(res);
      if (code === "token_expired") {
        if (await refreshOnce()) {
          res = await doFetch();
          if (res.status === 401) _onAuthLost?.();
        } else {
          _onAuthLost?.();
        }
      } else if (code === "unauthenticated" || code === "session_revoked") {
        _onAuthLost?.();
      }
    }
    if (!res.ok || !res.body) return;
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      if (chunk) onDelta(chunk);
    }
    const tail = decoder.decode(); // qalıq multibyte-ı boşalt
    if (tail) onDelta(tail);
  } catch {
    // şəbəkə xətası / abort — səssiz keç (UI köhnə vəziyyəti saxlayır)
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

/**
 * Bütün modul-səviyyəli keşləri / in-flight promise-ləri / prefetch dəstlərini
 * sıfırlayır. Giriş VƏ çıxış zamanı çağırılır ki, əvvəlki istifadəçinin datası
 * (overview, anomaliyalar, radar detalları, analog/proqnoz prefetch izləri)
 * yeni sessiyaya sızmasın.
 */
export function resetApiCaches(): void {
  _ovCache = null;
  _ovInflight = null;
  _anomCache = null;
  _anomInflight = null;
  _radarDetailCache.clear();
  _radarPrefetching.clear();
  _analogPrefetched.clear();
  _forecastPrefetched.clear();
}
