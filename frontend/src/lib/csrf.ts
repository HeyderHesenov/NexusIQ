/**
 * CSRF cookie oxuyucusu.
 *
 * Backend CSRF token-ini JS-oxunan (httpOnly OLMAYAN) cookie-də saxlayır:
 *   • dev-də  → `nexusiq_csrf`
 *   • prod-da → `__Host-nexusiq_csrf`
 * Hansı mövcuddursa oxunur. Hər təhlükəsiz-olmayan (POST/PUT/PATCH/DELETE)
 * sorğuda bu dəyər `X-CSRF-Token` başlığı kimi göndərilməlidir — backend
 * middleware həm bu başlığı, həm də Origin-i yoxlayır.
 */
const CSRF_COOKIE_NAMES = ["__Host-nexusiq_csrf", "nexusiq_csrf"] as const;

/** Cari CSRF token-i qaytarır (yoxdursa `null`). Yalnız brauzerdə işləyir. */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const jar = document.cookie ? document.cookie.split("; ") : [];
  for (const name of CSRF_COOKIE_NAMES) {
    const prefix = `${name}=`;
    const hit = jar.find((c) => c.startsWith(prefix));
    if (hit) return decodeURIComponent(hit.slice(prefix.length));
  }
  return null;
}
