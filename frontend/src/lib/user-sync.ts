"use client";

/**
 * İstifadəçi datasının sinxron orkestratoru — auth-context çağırır.
 *
 *  • `hydrateUserData()` — auth-dan sonra bütün per-user store-ları serverdən
 *    doldurur (bloklamır; hər hook öz event-i ilə yenilənir).
 *  • `clearUserData()` — çıxışda hamısını boşaldır (əvvəlki istifadəçi sızmasın).
 *  • `resubscribePush()` — brauzerdə mövcud push abunəsi varsa serverə yenidən
 *    POST edir (idempotent) ki, indi authed olan istifadəçiyə bağlansın.
 */
import { apiPost } from "@/lib/api";
import { currentSubscription } from "@/lib/push";
import * as alerts from "@/lib/alerts";
import * as bookmarks from "@/lib/bookmarks";
import * as holdings from "@/lib/holdings";
import * as lastSeen from "@/lib/lastSeen";
import * as savedEvents from "@/lib/savedEvents";
import * as watchlist from "@/lib/watchlist";

const LANG_KEY = "nexusiq_lang";

/** Bütün store-ları serverdən yüklə (fire-and-forget; render-i bloklamır). */
export function hydrateUserData(): void {
  void watchlist.hydrate();
  void holdings.hydrate();
  void bookmarks.hydrate();
  void alerts.hydrate();
  void savedEvents.hydrate();
  void lastSeen.hydrate();
}

/** Bütün in-memory store-ları boşalt (çıxış). */
export function clearUserData(): void {
  watchlist.clearStore();
  holdings.clearStore();
  bookmarks.clearStore();
  alerts.clearStore();
  savedEvents.clearStore();
  lastSeen.clearStore();
}

/** Mövcud brauzer push abunəsini indiki istifadəçiyə yenidən bağla (self-heal). */
export async function resubscribePush(): Promise<void> {
  try {
    const sub = await currentSubscription();
    if (!sub) return;
    const json = sub.toJSON() as {
      endpoint: string;
      keys: { p256dh: string; auth: string };
    };
    let lang = "az";
    try {
      lang = localStorage.getItem(LANG_KEY) || "az";
    } catch {
      /* localStorage əlçatmaz */
    }
    await apiPost("/push/subscribe", {
      endpoint: json.endpoint,
      keys: json.keys,
      lang,
    });
  } catch {
    /* abunə yox / şəbəkə xətası — səssiz keç */
  }
}
