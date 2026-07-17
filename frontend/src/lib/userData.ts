/**
 * İstifadəçiyə aid brauzer datasının vahid siyahısı + təmizləmə.
 *
 * Niyə var: `logout()` YALNIZ `nexusiq_session`-u silirdi. Qalanları —
 * `nexusiq_holdings` (qty + avgCost = maliyyə PII), watchlist, alerts,
 * bookmarks, saved events, lastSeen — brauzerdə qalırdı. `AuthGate` isə
 * yalnız sessiya açarının MÖVCUDLUĞUNA baxır, `AuthScreen` isə istənilən
 * düzgün formatlı email + 6 simvolluq parolu qəbul edir. Nəticə: paylaşılan
 * brauzerdə çıxışdan sonra "qeydiyyatdan keçən" növbəti şəxs əvvəlkinin tam
 * portfelini və izləmə siyahısını hazır görürdü.
 *
 * Açarlar sahibi modullardan İDXAL olunur (əl ilə təkrarlanmır) — belə ki, yeni
 * data modulu əlavə edən adam açarı burada da yazmağı unutsa belə, siyahı
 * mənbədən qopa bilməz.
 *
 * QEYD: `nexusiq_theme` və `nexusiq_lang` QƏSDƏN daxil deyil — onlar cihaz
 * tərcihidir, istifadəçi datası deyil (PII deyil), və çıxışda sıfırlanması
 * yalnız qıcıqlandırıcı olardı.
 */
import { KEY as ALERTS_KEY } from "./alerts";
import { KEY as BOOKMARKS_KEY } from "./bookmarks";
import { KEY as HOLDINGS_KEY } from "./holdings";
import { KEY as LAST_SEEN_KEY } from "./lastSeen";
import { KEY as SAVED_EVENTS_KEY } from "./savedEvents";
import { KEY as WATCHLIST_KEY } from "./watchlist";

export const SESSION_KEY = "nexusiq_session";

/** İstifadəçiyə aid (şəxsi) bütün açarlar — sessiya istisna. */
export const USER_DATA_KEYS: readonly string[] = [
  HOLDINGS_KEY,
  WATCHLIST_KEY,
  BOOKMARKS_KEY,
  ALERTS_KEY,
  SAVED_EVENTS_KEY,
  LAST_SEEN_KEY,
];

/** Şəxsi datanı silir (sessiya daxil). Çıxışda çağırılır. */
export function clearUserData(): void {
  for (const k of [SESSION_KEY, ...USER_DATA_KEYS]) {
    localStorage.removeItem(k);
  }
}
