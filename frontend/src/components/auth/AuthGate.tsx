"use client";

import { AuthFlow } from "./AuthFlow";
import { useAuth } from "@/lib/auth-context";

/**
 * Saytı qoruyan qapı. Real sessiya `AuthProvider` (fetchMe) ilə yoxlanır:
 * yüklənmə bitənə qədər boş fon, sessiya yoxdursa giriş axını, varsa əsas sayt.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();

  // Bootstrap bitənə qədər boş fon — yanıp-sönməni önləyir.
  if (status === "loading") {
    return <div className="min-h-screen bg-bg" />;
  }

  if (status === "anon") {
    return <AuthFlow />;
  }

  return <>{children}</>;
}
