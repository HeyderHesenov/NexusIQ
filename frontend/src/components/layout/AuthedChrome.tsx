"use client";

import { AIAssistantFab } from "@/components/ai/AIAssistantFab";
import { MigrateBanner } from "@/components/system/MigrateBanner";
import { useAuth } from "@/lib/auth-context";

/**
 * Yalnız authed istifadəçiyə görünən üzən elementlər (AI Analitik + köçürmə
 * banneri). AuthGate əsas route-u bükür; bu chrome ondan ayrıdır ki, publik
 * marşrutlarda (məs. `/reset`) və giriş ekranında görünməsin.
 */
export function AuthedChrome() {
  const { status } = useAuth();
  if (status !== "authed") return null;
  return (
    <>
      <AIAssistantFab />
      <MigrateBanner />
    </>
  );
}
