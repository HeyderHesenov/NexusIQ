/**
 * Autentifikasiya API çağırışları (tipli).
 *
 * Bu çağırışlar QƏSDƏN `lib/api.ts`-in ümumi `_tracked` retry məntiqindən
 * KEÇMİR: refresh sonsuz döngüyə düşməsin, login-in 401-i (invalid_credentials)
 * yanlışlıqla "auth itkisi" saymasın deyə. Bunun əvəzinə hər çağırış xətanı
 * server `code`-u ilə (`ApiError`) atır → UI onu i18n mesajına map edir.
 *
 * Bütün sorğular eyni-origin `/backend` proksisi üzərindən gedir + cookie-lər
 * (`credentials:"include"`); təhlükəsiz-olmayan metodlara CSRF başlığı əlavə olunur.
 */
import { ApiError } from "./api";
import { getCsrfToken } from "./csrf";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/backend";
const TIMEOUT_MS = 10_000;

/** Backend-in qaytardığı istifadəçi (camelCase). */
export interface AiBudget {
  dailyUsed: number;
  dailyLimit: number;
}

export interface UserOut {
  id: string;
  email: string;
  displayName: string | null;
  avatarUrl: string | null;
  role: string;
  emailVerified: boolean;
  aiBudget?: AiBudget;
}

async function readCode(res: Response): Promise<string | undefined> {
  try {
    const d = await res.clone().json();
    return d?.detail?.code ?? d?.code ?? undefined;
  } catch {
    return undefined;
  }
}

async function authRequest<T>(
  path: string,
  method: "GET" | "POST" | "DELETE",
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (method !== "GET") {
    const token = getCsrfToken();
    if (token) headers["X-CSRF-Token"] = token;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      credentials: "include",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(TIMEOUT_MS),
      cache: "no-store",
    });
  } catch {
    // Şəbəkə / timeout xətası — status 0.
    throw new ApiError(0, "network_error", path);
  }

  if (!res.ok) {
    throw new ApiError(res.status, await readCode(res), path);
  }

  // 200/202 — bəzi cavablar boş ola bilər (logout, register).
  try {
    return (await res.json()) as T;
  } catch {
    return undefined as T;
  }
}

/** E-poçt/parol girişi → UserOut + cookie-lər. */
export function login(email: string, password: string): Promise<UserOut> {
  return authRequest<UserOut>("/auth/login", "POST", { email, password });
}

/** Qeydiyyat → 202 {ok}. Enumeration-safe; ASLA avtomatik giriş etmir. */
export function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<{ ok: boolean }> {
  return authRequest<{ ok: boolean }>("/auth/register", "POST", {
    email,
    password,
    displayName,
  });
}

/** Cari sessiyadan çıxış → cookie-lər təmizlənir. */
export function logout(): Promise<{ ok?: boolean }> {
  return authRequest<{ ok?: boolean }>("/auth/logout", "POST", {});
}

/** Bütün cihazlardan çıxış (auth tələb edir). */
export function logoutAll(): Promise<{ ok?: boolean }> {
  return authRequest<{ ok?: boolean }>("/auth/logout-all", "POST", {});
}

/** Cari istifadəçini gətirir (bootstrap üçün). */
export function fetchMe(): Promise<UserOut> {
  return authRequest<UserOut>("/auth/me", "GET");
}

/** Parolu dəyişir (auth). */
export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ ok?: boolean }> {
  return authRequest<{ ok?: boolean }>("/auth/password", "POST", {
    currentPassword,
    newPassword,
  });
}

/** Parol sıfırlama linki istəyir → 202. */
export function requestReset(email: string): Promise<{ ok?: boolean }> {
  return authRequest<{ ok?: boolean }>("/auth/password-reset/request", "POST", {
    email,
  });
}

/** Parol sıfırlamanı token ilə təsdiqləyir. */
export function confirmReset(
  token: string,
  password: string,
): Promise<{ ok?: boolean }> {
  return authRequest<{ ok?: boolean }>("/auth/password-reset/confirm", "POST", {
    token,
    password,
  });
}

/** Google giriş üçün birdəfəlik nonce (qısa cookie də qoyulur). */
export function googleNonce(): Promise<{ nonce: string }> {
  return authRequest<{ nonce: string }>("/auth/google/nonce", "GET");
}

/** Google ID token (JWT) ilə giriş → UserOut + cookie-lər. */
export function googleLogin(credential: string): Promise<UserOut> {
  return authRequest<UserOut>("/auth/google", "POST", { credential });
}

/** Aktiv sessiya ("cihaz"). `current` = bu brauzerin sessiyası (ləğv edilə bilməz). */
export interface Session {
  id: string;
  userAgent: string | null;
  ip: string | null;
  createdAt: string | null;
  lastUsedAt: string | null;
  current: boolean;
}

/** İstifadəçinin aktiv sessiyaları — ən son işlənən əvvəl. */
export function listSessions(): Promise<Session[]> {
  return authRequest<Session[]>("/auth/sessions", "GET");
}

/** Tək bir sessiyanı ("cihazı") ləğv et. */
export function revokeSession(sid: string): Promise<{ ok?: boolean }> {
  return authRequest<{ ok?: boolean }>(
    `/auth/sessions/${encodeURIComponent(sid)}`,
    "DELETE",
  );
}
