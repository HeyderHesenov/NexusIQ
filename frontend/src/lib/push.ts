/**
 * Web Push köməkçiləri — Service Worker qeydiyyatı, icazə, abunə.
 * Bütün brauzer API-ləri burada cəmləşir; UI sadəcə bu funksiyaları çağırır.
 */
import { apiGet, apiPost } from "./api";

/** Brauzer Web Push-u dəstəkləyir? */
export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** Hazırkı icazə vəziyyəti: "default" | "granted" | "denied". */
export function permissionState(): NotificationPermission {
  if (typeof Notification === "undefined") return "denied";
  return Notification.permission;
}

/** base64url VAPID açarını Uint8Array-ə çevirir (PushManager tələbi). */
function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

async function registerSW(): Promise<ServiceWorkerRegistration> {
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  return reg;
}

/** Cari abunə varmı? (SW qeydiyyatdan keçibsə) */
export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return null;
  return reg.pushManager.getSubscription();
}

/** İcazə istə + abunə yarat + backend-ə saxla. true = uğurlu. */
export async function enablePush(lang: string): Promise<boolean> {
  if (!pushSupported()) return false;

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return false;

  const { publicKey, enabled } = await apiGet<{
    publicKey: string;
    enabled: boolean;
  }>("/push/key");
  if (!enabled || !publicKey) return false;

  const reg = await registerSW();
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }

  const json = sub.toJSON() as {
    endpoint: string;
    keys: { p256dh: string; auth: string };
  };
  await apiPost("/push/subscribe", {
    endpoint: json.endpoint,
    keys: json.keys,
    lang,
  });
  return true;
}

/** Abunəni ləğv et — brauzerdə və backend-də. */
export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  try {
    await sub.unsubscribe();
  } catch {
    /* yoxla */
  }
  try {
    await apiPost("/push/unsubscribe", { endpoint });
  } catch {
    /* backend əlçatmazdırsa səssiz keç */
  }
}

/** Test bildirişi göndər (yoxlama). */
export async function sendTestPush(): Promise<void> {
  await apiPost("/push/test", {});
}
