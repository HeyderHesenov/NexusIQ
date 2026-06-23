"use client";

import { useState } from "react";
import { Mail, Lock, User } from "lucide-react";
import { Ticker } from "@/components/market/Ticker";
import { useI18n } from "@/lib/i18n";
import {
  signInWithGoogle,
  googleConfigured,
  type GoogleUser,
} from "@/lib/google";

type Mode = "login" | "signup";

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

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function AuthScreen({
  onAuthed,
  authKey,
}: {
  onAuthed: () => void;
  authKey: string;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function persist(user: GoogleUser) {
    localStorage.setItem(authKey, JSON.stringify(user));
    onAuthed();
  }

  /** E-poçt/parol ilə daxil olma — hələlik demo (real auth backend addımında). */
  async function handleEmail(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (mode === "signup" && !name.trim()) {
      setError(t("auth.nameRequired"));
      return;
    }
    if (!EMAIL_RE.test(email)) {
      setError(t("auth.invalidEmail"));
      return;
    }
    if (password.length < 6) {
      setError(t("auth.shortPassword"));
      return;
    }

    setBusy(true);
    await new Promise((r) => setTimeout(r, 400));
    const displayName =
      mode === "signup" ? name.trim() : email.split("@")[0];
    persist({ name: displayName, email });
  }

  async function handleGoogle() {
    setError(null);
    setBusy(true);
    try {
      let user: GoogleUser;
      if (googleConfigured()) {
        user = await signInWithGoogle();
      } else {
        await new Promise((r) => setTimeout(r, 500));
        user = { name: "Demo İstifadəçi", email: "demo@nexusiq.az" };
      }
      persist(user);
    } catch {
      setError(t("auth.error"));
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      {/* ambient parıltı */}
      <div className="pointer-events-none absolute top-1/4 h-96 w-96 rounded-full bg-accent/10 blur-[130px]" />

      <div className="relative w-full max-w-sm fade-up">
        <div className="mb-7 flex items-center justify-center gap-2.5">
          <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="text-lg font-semibold tracking-tight">
            Nexus<span className="text-accent">IQ</span>
          </span>
        </div>

        {/* rejim keçidi */}
        <div className="mx-auto mb-6 flex w-full max-w-[260px] rounded-xl border border-border bg-surface p-1">
          {(["login", "signup"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-200 ${
                mode === m
                  ? "bg-accent text-black"
                  : "text-muted hover:text-text"
              }`}
            >
              {m === "login" ? t("auth.tabLogin") : t("auth.tabSignup")}
            </button>
          ))}
        </div>

        <h2 className="text-center text-2xl font-semibold tracking-tight">
          {mode === "login" ? t("auth.welcome") : t("auth.createTitle")}
        </h2>
        <p className="mt-2 text-center text-sm text-muted">
          {mode === "login" ? t("auth.subtitle") : t("auth.createSubtitle")}
        </p>

        {/* e-poçt formu */}
        <form onSubmit={handleEmail} className="mt-6 space-y-3 text-left">
          {mode === "signup" && (
            <Field
              icon={<User size={16} />}
              type="text"
              placeholder={t("auth.namePh")}
              value={name}
              onChange={setName}
              autoComplete="name"
            />
          )}
          <Field
            icon={<Mail size={16} />}
            type="email"
            placeholder={t("auth.emailPh")}
            value={email}
            onChange={setEmail}
            autoComplete="email"
          />
          <Field
            icon={<Lock size={16} />}
            type="password"
            placeholder={t("auth.passwordPh")}
            value={password}
            onChange={setPassword}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />

          <button
            type="submit"
            disabled={busy}
            className="mt-1 flex w-full items-center justify-center rounded-xl bg-accent py-3.5 text-sm font-semibold text-black transition-all duration-200 hover:brightness-110 active:translate-y-px disabled:opacity-60"
          >
            {busy
              ? t("auth.loading")
              : mode === "login"
                ? t("auth.submitLogin")
                : t("auth.submitSignup")}
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-lg border border-down/30 bg-down/10 px-3 py-2 text-center text-sm text-down">
            {error}
          </p>
        )}

        {/* ayırıcı */}
        <div className="my-6 flex items-center gap-3">
          <span className="h-px flex-1 bg-border" />
          <span className="text-xs uppercase tracking-wider text-muted">
            {t("auth.or")}
          </span>
          <span className="h-px flex-1 bg-border" />
        </div>

        {/* alternativ — Google */}
        <button
          onClick={handleGoogle}
          disabled={busy}
          className="group flex w-full items-center justify-center gap-3 rounded-xl border border-border bg-white py-3.5 text-sm font-semibold text-[#1f1f22] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_var(--shadow)] active:translate-y-0 disabled:opacity-60"
        >
          <GoogleIcon />
          {t("auth.google")}
        </button>

        {!googleConfigured() && (
          <p className="mt-4 text-center text-xs text-muted">
            {t("auth.demoNote")}
          </p>
        )}

        <p className="mt-7 text-center text-xs leading-relaxed text-muted">
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

/** İkon + input sahəsi. */
function Field({
  icon,
  type,
  placeholder,
  value,
  onChange,
  autoComplete,
}: {
  icon: React.ReactNode;
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3.5 focus-within:border-accent">
      <span className="text-muted">{icon}</span>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-transparent py-3 text-sm text-text placeholder:text-muted/70 focus:outline-none"
      />
    </div>
  );
}
