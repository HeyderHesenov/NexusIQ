"use client";

import { useState } from "react";
import { IntroSplash } from "./IntroSplash";
import { AuthScreen } from "./AuthScreen";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

/**
 * Giriş axını: əvvəl Market Boot intro (landing).
 * Avtomatik keçid YOXDUR — istifadəçi CTA-ya toxunanda giriş açılır.
 * Uğurlu girişdə `AuthProvider` status-u dəyişir → `AuthGate` saytı açır.
 */
export function AuthFlow() {
  const [phase, setPhase] = useState<"intro" | "auth">("intro");

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* dil seçici — həm intro, həm giriş üstündə */}
      <div className="absolute right-5 top-5 z-50">
        <LanguageSwitcher />
      </div>

      <div
        className={`phase-fade absolute inset-0 origin-center ${
          phase === "intro"
            ? "scale-100 opacity-100"
            : "pointer-events-none scale-105 opacity-0"
        }`}
      >
        <IntroSplash onEnter={() => setPhase("auth")} />
      </div>

      <div
        className={`phase-fade absolute inset-0 ${
          phase === "auth"
            ? "scale-100 opacity-100"
            : "pointer-events-none scale-95 opacity-0"
        }`}
      >
        <AuthScreen />
      </div>
    </div>
  );
}
