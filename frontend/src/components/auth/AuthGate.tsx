"use client";

import { useEffect, useState } from "react";
import { AuthFlow } from "./AuthFlow";

const AUTH_KEY = "nexusfx_session";

/**
 * Saytı qoruyan qapı. Sessiya yoxdursa giriş ekranı göstərilir,
 * uğurlu girişdən sonra əsas sayt açılır.
 *
 * Qeyd: hələlik sessiya brauzerdə saxlanılır. Backend autentifikasiyası
 * sonrakı addımda real JWT ilə əvəz olunacaq.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(localStorage.getItem(AUTH_KEY)));
    setReady(true);
  }, []);

  // Hidratasiya bitənə qədər boş fon — yanıp-sönməni önləyir.
  if (!ready) {
    return <div className="min-h-screen bg-bg" />;
  }

  if (!authed) {
    return <AuthFlow onAuthed={() => setAuthed(true)} authKey={AUTH_KEY} />;
  }

  return <>{children}</>;
}
