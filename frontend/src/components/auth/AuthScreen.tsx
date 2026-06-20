"use client";

import { useState } from "react";
import { Ticker } from "@/components/market/Ticker";
import { useI18n } from "@/lib/i18n";
import {
  signInWithGoogle,
  googleConfigured,
  type GoogleUser,
} from "@/lib/google";

/** Rəsmi Google "G" loqosu. */
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.96A9 9 0 0 0 0 9c0 1.45.35 2.82.96 4.05l3.01-2.33Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.47.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  );
}

export function AuthScreen({
  onAuthed,
  authKey,
}: {
  onAuthed: () => void;
  authKey: string;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGoogle() {
    setError(null);
    setBusy(true);
    try {
      let user: GoogleUser;
      if (googleConfigured()) {
        user = await signInWithGoogle();
      } else {
        // Demo rejimi — Client ID əlavə olunanda real Gmail işləyəcək.
        await new Promise((r) => setTimeout(r, 500));
        user = { name: "Demo İstifadəçi", email: "demo@nexusfx.az" };
      }
      localStorage.setItem(authKey, JSON.stringify(user));
      onAuthed();
    } catch {
      setError(t("auth.error"));
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      {/* ambient parıltı */}
      <div className="pointer-events-none absolute top-1/4 h-96 w-96 rounded-full bg-accent/10 blur-[130px]" />

      <div className="relative w-full max-w-sm text-center fade-up">
        <div className="mb-8 flex items-center justify-center gap-2.5">
          <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="text-lg font-semibold tracking-tight">
            Nexus<span className="text-accent">FX</span>
          </span>
        </div>

        <h2 className="text-2xl font-semibold tracking-tight">
          {t("auth.welcome")}
        </h2>
        <p className="mt-2 text-sm text-muted">{t("auth.subtitle")}</p>

        <button
          onClick={handleGoogle}
          disabled={busy}
          className="group mt-7 flex w-full items-center justify-center gap-3 rounded-xl border border-border bg-white py-3.5 text-sm font-semibold text-[#1f1f22] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_rgba(255,255,255,0.25)] active:translate-y-0 disabled:opacity-60"
        >
          {busy ? (
            <span className="text-muted">{t("auth.loading")}</span>
          ) : (
            <>
              <GoogleIcon />
              {t("auth.google")}
            </>
          )}
        </button>

        {error && (
          <p className="mt-4 rounded-lg border border-down/30 bg-down/10 px-3 py-2 text-sm text-down">
            {error}
          </p>
        )}

        {!googleConfigured() && (
          <p className="mt-4 text-xs text-muted">{t("auth.demoNote")}</p>
        )}

        <p className="mt-8 text-xs leading-relaxed text-muted">
          {t("auth.terms")}
        </p>
      </div>

      {/* terminal imzası — alt ticker */}
      <div className="absolute inset-x-0 bottom-0">
        <Ticker />
      </div>
    </div>
  );
}
