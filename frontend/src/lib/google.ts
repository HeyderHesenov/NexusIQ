/**
 * Google Identity Services (GIS) ilə Gmail girişi.
 * Real giriş üçün NEXT_PUBLIC_GOOGLE_CLIENT_ID lazımdır.
 * ID yoxdursa demo rejimi işləyir (lokal test üçün).
 */

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export interface GoogleUser {
  name: string;
  email: string;
  picture?: string;
}

export const googleConfigured = (): boolean => Boolean(CLIENT_ID);

let gisPromise: Promise<void> | null = null;

function loadGis(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if ((window as any).google?.accounts) return Promise.resolve();
  if (gisPromise) return gisPromise;

  gisPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Google skripti yüklənmədi"));
    document.head.appendChild(s);
  });
  return gisPromise;
}

/** Google hesab seçicisini açır və istifadəçi profilini qaytarır. */
export async function signInWithGoogle(): Promise<GoogleUser> {
  await loadGis();

  return new Promise((resolve, reject) => {
    const tokenClient = (window as any).google.accounts.oauth2.initTokenClient({
      client_id: CLIENT_ID,
      scope: "openid email profile",
      callback: async (resp: any) => {
        if (resp.error) {
          reject(new Error(resp.error));
          return;
        }
        try {
          const r = await fetch(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            { headers: { Authorization: `Bearer ${resp.access_token}` } },
          );
          const u = await r.json();
          resolve({ name: u.name, email: u.email, picture: u.picture });
        } catch (e) {
          reject(e as Error);
        }
      },
    });
    tokenClient.requestAccessToken();
  });
}
