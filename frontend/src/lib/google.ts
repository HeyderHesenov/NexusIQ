/**
 * Google Identity Services (GIS) — ID token axını.
 *
 * Brauzer artıq `googleapis.com/userinfo`-ya GETMIR. Əvəzinə GIS bir imzalı
 * ID token (JWT) qaytarır, o da backend-ə (`POST /auth/google`) göndərilir —
 * yoxlama və sessiya server tərəfdə qurulur. Nonce backend-dən alınır
 * (`GET /auth/google/nonce`) və token-in içinə bağlanır (replay müdafiəsi).
 *
 * Real giriş üçün NEXT_PUBLIC_GOOGLE_CLIENT_ID lazımdır; boş qalsa düymə
 * deaktiv olur (demo yolu YOXDUR).
 */
import { googleNonce } from "./auth";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export const googleConfigured = (): boolean => Boolean(CLIENT_ID);

interface CredentialResponse {
  credential?: string;
}

interface PromptNotification {
  isNotDisplayed?: () => boolean;
  isSkippedMoment?: () => boolean;
  isDismissedMoment?: () => boolean;
  getNotDisplayedReason?: () => string;
  getSkippedReason?: () => string;
  getDismissedReason?: () => string;
}

interface GoogleIdApi {
  initialize(config: {
    client_id: string;
    nonce?: string;
    callback: (resp: CredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
    use_fedcm_for_prompt?: boolean;
  }): void;
  prompt(listener?: (notification: PromptNotification) => void): void;
  cancel(): void;
}

interface GoogleGlobal {
  accounts?: { id: GoogleIdApi };
}

function gis(): GoogleGlobal | undefined {
  return (globalThis as { google?: GoogleGlobal }).google;
}

let gisPromise: Promise<void> | null = null;

function loadGis(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (gis()?.accounts) return Promise.resolve();
  if (gisPromise) return gisPromise;

  gisPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("google_script_failed"));
    document.head.appendChild(s);
  });
  return gisPromise;
}

/**
 * Google hesab seçicisini açır və imzalı ID token-i (JWT `credential`) qaytarır.
 * İstifadəçi ləğv edərsə / göstərilə bilməzsə xəta atır.
 */
export async function signInWithGoogle(): Promise<string> {
  if (!CLIENT_ID) throw new Error("google_not_configured");
  await loadGis();

  const api = gis()?.accounts?.id;
  if (!api) throw new Error("google_unavailable");

  const { nonce } = await googleNonce();

  return new Promise<string>((resolve, reject) => {
    let settled = false;
    const done = (fn: () => void) => {
      if (settled) return;
      settled = true;
      fn();
    };

    api.initialize({
      client_id: CLIENT_ID,
      nonce,
      cancel_on_tap_outside: true,
      callback: (resp) => {
        if (resp.credential) done(() => resolve(resp.credential as string));
        else done(() => reject(new Error("google_no_credential")));
      },
    });

    api.prompt((n) => {
      // Uğur callback vasitəsilə gəlir; burada yalnız uğursuz anları ləğv edirik.
      if (n.isNotDisplayed?.()) done(() => reject(new Error("google_not_displayed")));
      else if (n.isSkippedMoment?.()) done(() => reject(new Error("google_skipped")));
      else if (
        n.isDismissedMoment?.() &&
        n.getDismissedReason?.() !== "credential_returned"
      ) {
        done(() => reject(new Error("google_dismissed")));
      }
    });
  });
}
