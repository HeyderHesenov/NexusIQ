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

/** AI Asistanta sual göndərir (arxa fonda ikili AI debate). */
export async function sendChat(
  message: string,
  lang: string,
): Promise<{ answer: string; refused: boolean }> {
  return apiPost("/chat", { message, lang });
}

export { API_BASE };
