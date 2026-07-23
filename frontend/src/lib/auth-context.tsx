"use client";

/**
 * Auth vəziyyətinin qlobal mənbəyi.
 *
 * Bootstrap-da `fetchMe()` çağırır (localStorage yoxlamasını əvəz edir):
 *   • 200 → `authed`
 *   • token vaxtı keçibsə → bir dəfə səssiz refresh cəhdi → uğurda `authed`
 *   • qalan 401 → `anon`
 *
 * Sərt 401-lər (data endpoint-lərindən) `setOnAuthLost` vasitəsilə tutulur və
 * dərhal `anon`-a keçir. Çıxış/giriş `BroadcastChannel` ilə tab-lar arası
 * sinxronlaşır.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ApiError,
  refreshOnce,
  resetApiCaches,
  setOnAuthLost,
} from "./api";
import {
  fetchMe,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  logoutAll as apiLogoutAll,
  googleLogin as apiGoogleLogin,
  type UserOut,
} from "./auth";
import { clearUserData, hydrateUserData, resubscribePush } from "./user-sync";

type Status = "loading" | "authed" | "anon";

interface AuthContextValue {
  user: UserOut | null;
  status: Status;
  login: (email: string, password: string) => Promise<UserOut>;
  register: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<UserOut>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const CHANNEL = "nexusiq-auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const bcRef = useRef<BroadcastChannel | null>(null);

  const applyUser = useCallback((u: UserOut) => {
    setUser(u);
    setStatus("authed");
  }, []);

  const applyAnon = useCallback(() => {
    setUser(null);
    setStatus("anon");
  }, []);

  const refreshMe = useCallback(async () => {
    try {
      applyUser(await fetchMe());
    } catch (e) {
      // Access YOXDUR (cookie max-age=10dəq silinib) VƏ YA vaxtı keçib → hər iki halda
      // 401 gəlir (`unauthenticated` və ya `token_expired`). Refresh token (30g) hələ
      // yaşaya bilər → BİR səssiz refresh cəhdi. Yalnız 401-lərdə (5xx-də mənasız).
      if (e instanceof ApiError && e.status === 401) {
        if (await refreshOnce()) {
          try {
            applyUser(await fetchMe());
            return;
          } catch {
            /* aşağı düşür → anon */
          }
        }
      }
      applyAnon();
    }
  }, [applyUser, applyAnon]);

  // Bootstrap — mount-da bir dəfə.
  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  // Sərt 401 (istənilən data endpoint-i) → giriş ekranına.
  useEffect(() => {
    setOnAuthLost(() => applyAnon());
    return () => setOnAuthLost(null);
  }, [applyAnon]);

  // Auth vəziyyəti dəyişəndə per-user store-ları sinxronla: authed → serverdən
  // yüklə + push abunəsini yenidən bağla; anon → yaddaşı boşalt. Render bloklanmır.
  useEffect(() => {
    if (status === "authed") {
      hydrateUserData();
      void resubscribePush();
    } else if (status === "anon") {
      clearUserData();
    }
  }, [status]);

  // Tab-lar arası sinxron.
  useEffect(() => {
    if (typeof window === "undefined" || typeof BroadcastChannel === "undefined") {
      return;
    }
    const bc = new BroadcastChannel(CHANNEL);
    bcRef.current = bc;
    bc.onmessage = (ev: MessageEvent) => {
      if (ev.data === "logout") applyAnon();
      else if (ev.data === "login") void refreshMe();
    };
    return () => {
      bc.close();
      bcRef.current = null;
    };
  }, [applyAnon, refreshMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const u = await apiLogin(email, password);
      resetApiCaches(); // əvvəlki istifadəçinin keşi sızmasın
      applyUser(u);
      bcRef.current?.postMessage("login");
      return u;
    },
    [applyUser],
  );

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      // 202, sessiya yaratmır — avtomatik giriş çağıran tərəfə buraxılır.
      await apiRegister(email, password, displayName);
    },
    [],
  );

  const loginWithGoogle = useCallback(
    async (credential: string) => {
      const u = await apiGoogleLogin(credential);
      resetApiCaches();
      applyUser(u);
      bcRef.current?.postMessage("login");
      return u;
    },
    [applyUser],
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Server əlçatmaz olsa belə lokal olaraq təmizlə.
    }
    resetApiCaches();
    applyAnon();
    bcRef.current?.postMessage("logout");
  }, [applyAnon]);

  // Bütün cihazlardan çıx: server sessions_valid_from-u bump edir → cari sessiya da
  // ölür, ona görə lokal olaraq anon-a keçirik (logout ilə eyni).
  const logoutAll = useCallback(async () => {
    try {
      await apiLogoutAll();
    } catch {
      // Server əlçatmaz olsa belə lokal olaraq təmizlə.
    }
    resetApiCaches();
    applyAnon();
    bcRef.current?.postMessage("logout");
  }, [applyAnon]);

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        login,
        register,
        loginWithGoogle,
        logout,
        logoutAll,
        refreshMe,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth AuthProvider daxilində işlədilməlidir");
  return ctx;
}
