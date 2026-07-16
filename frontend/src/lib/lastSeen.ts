"use client";

/**
 * Son-baxış vaxtı — localStorage-da epoch ms. "Sən yox ikən" sayğacı üçün:
 * digest serverə bu vaxtı göndərir, server ondan sonrakı xəbərləri sayır.
 * Hesab yoxdur (demo auth) — tamamilə klient tərəfli.
 */
const KEY = "nexusiq_lastseen";

export function getLastSeen(): number | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/** Digest göründükdən sonra çağır — növbəti açılışda "yeni" bundan sonrakılardır. */
export function markSeen(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, String(Date.now()));
}
