"use client";

import { usePathname } from "next/navigation";
import { AuthFlow } from "./AuthFlow";
import { useAuth } from "@/lib/auth-context";

/** Sessiya tələb etməyən publik marşrutlar (e-poçt linkindən açılır). */
const PUBLIC_PATHS = new Set(["/reset"]);

/**
 * Saytı qoruyan qapı. Real sessiya `AuthProvider` (fetchMe) ilə yoxlanır:
 * yüklənmə bitənə qədər boş fon, sessiya yoxdursa giriş axını, varsa əsas sayt.
 * İstisna: parol sıfırlama kimi publik marşrutlar auth-dan asılı olmadan render olunur.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const pathname = usePathname();

  // Publik marşrut — auth bootstrap-ı gözləmədən dərhal göstər.
  if (pathname && PUBLIC_PATHS.has(pathname)) {
    return <>{children}</>;
  }

  // Bootstrap bitənə qədər boş fon — yanıp-sönməni önləyir.
  if (status === "loading") {
    return <div className="min-h-screen bg-bg" />;
  }

  if (status === "anon") {
    return <AuthFlow />;
  }

  return <>{children}</>;
}
