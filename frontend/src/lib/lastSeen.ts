"use client";

/**
 * Son-baxış vaxtı — serverdəki `/me/prefs.lastSeenAt` ilə dəstəklənir (epoch ms).
 * "Sən yox ikən" sayğacı üçün: /me/intel/* serverin özündə bu vaxtı oxuyur.
 * Klient tərəfdə yalnız in-memory kopya saxlanır (hydrate ilə doldurulur);
 * `markSeen` optimistik yaddaşı yeniləyir və fon PUT ilə serverə yazır.
 */
import { apiGet, apiPut } from "@/lib/api";

export const KEY = "nexusiq_lastseen";

let lastSeen: number | null = null;

/** Serverdən prefs.lastSeenAt-i yüklə. Auth-dan sonra bir dəfə. */
export async function hydrate(): Promise<void> {
  try {
    const p = await apiGet<{ lastSeenAt: string | null }>("/me/prefs");
    lastSeen = p?.lastSeenAt ? Date.parse(p.lastSeenAt) || null : null;
  } catch {
    /* köhnə dəyər qalır */
  }
}

/** Çıxışda in-memory dəyəri sıfırla. */
export function clearStore(): void {
  lastSeen = null;
}

export function getLastSeen(): number | null {
  return lastSeen;
}

/** Digest göründükdən sonra çağır — növbəti açılışda "yeni" bundan sonrakılardır. */
export function markSeen(): void {
  lastSeen = Date.now();
  void apiPut("/me/prefs", { lastSeen }).catch(() => {
    /* şəbəkə xətası — server növbəti markSeen-də yenilənəcək */
  });
}
