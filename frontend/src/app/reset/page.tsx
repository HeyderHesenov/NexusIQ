"use client";

/**
 * Parol sıfırlama səhifəsi (`/reset?token=…`).
 *
 * E-poçtdakı linkdən açılır. Anon istifadəçi üçün əlçatandır — `AuthGate`
 * bu marşrutu qapıdan keçirir. Token `consume_reset_token` ilə birdəfəlik
 * yandırılır; uğurda avtomatik giriş YOXDUR (istifadəçi yeni parolla girir).
 */
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Lock, KeyRound, CheckCircle2 } from "lucide-react";
import { Ticker } from "@/components/market/Ticker";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useI18n } from "@/lib/i18n";
import { confirmReset } from "@/lib/auth";
import { ApiError } from "@/lib/api";

/** Server `code`-unu i18n açarına map edir — xam server mətni ASLA göstərilmir. */
function resetErrorKey(err: unknown): string {
  const code = err instanceof ApiError ? err.code : undefined;
  switch (code) {
    case "invalid_token":
    case "token_expired":
      return "auth.resetInvalid";
    case "password_breached":
    case "breached_password":
    case "pwned_password":
      return "auth.passwordBreached";
    case "password_too_short":
    case "password_too_long":
    case "password_invalid":
    case "weak_password":
      return "auth.passwordTooShort";
    default:
      return "auth.genericError";
  }
}

function ResetForm() {
  const { t } = useI18n();
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!token) {
      setError(t("auth.resetInvalid"));
      return;
    }
    // Klient yoxlamaları yalnız UX üçün — əsl mərci server (min 12, HIBP).
    if (password.length < 12) {
      setError(t("auth.passwordTooShort"));
      return;
    }
    if (password !== confirm) {
      setError(t("auth.passwordMismatch"));
      return;
    }
    setBusy(true);
    try {
      await confirmReset(token, password);
      setDone(true);
    } catch (err) {
      setError(t(resetErrorKey(err)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative w-full max-w-sm fade-up">
      {/* wordmark */}
      <div className="mb-7 flex items-center justify-center gap-2.5">
        <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
        <span className="text-lg font-semibold tracking-tight">
          Nexus<span className="text-accent">IQ</span>
        </span>
      </div>

      {done ? (
        <div className="flex flex-col items-center gap-4 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full border border-up/30 bg-up/10">
            <CheckCircle2 size={26} className="text-up" />
          </span>
          <p className="text-sm text-text">{t("auth.resetSuccess")}</p>
          <Link
            href="/"
            className="mt-1 flex w-full items-center justify-center rounded-xl bg-accent py-3.5 text-sm font-semibold text-black transition-all duration-200 hover:brightness-110 active:translate-y-px"
          >
            {t("auth.goToLogin")}
          </Link>
        </div>
      ) : (
        <>
          <div className="mb-3 flex justify-center">
            <span className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface text-accent">
              <KeyRound size={20} />
            </span>
          </div>
          <h2 className="text-center text-2xl font-semibold tracking-tight">
            {t("auth.resetTitle")}
          </h2>
          <p className="mt-2 text-center text-sm text-muted">
            {t("auth.resetSubtitle")}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-3 text-left">
            <PasswordField
              placeholder={t("auth.newPasswordPh")}
              value={password}
              onChange={setPassword}
            />
            <PasswordField
              placeholder={t("auth.confirmPasswordPh")}
              value={confirm}
              onChange={setConfirm}
            />
            <button
              type="submit"
              disabled={busy}
              className="mt-1 flex w-full items-center justify-center rounded-xl bg-accent py-3.5 text-sm font-semibold text-black transition-all duration-200 hover:brightness-110 active:translate-y-px disabled:opacity-60"
            >
              {busy ? t("auth.loading") : t("auth.resetSubmit")}
            </button>
          </form>

          {error && (
            <p className="mt-4 rounded-lg border border-down/30 bg-down/10 px-3 py-2 text-center text-sm text-down">
              {error}
            </p>
          )}

          <Link
            href="/"
            className="mt-6 block text-center text-xs text-muted transition-colors hover:text-text"
          >
            {t("auth.backToLogin")}
          </Link>
        </>
      )}
    </div>
  );
}

/** İkon + parol input sahəsi (AuthScreen `Field`-i ilə eyni görünüş). */
function PasswordField({
  placeholder,
  value,
  onChange,
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3.5 focus-within:border-accent">
      <span className="text-muted">
        <Lock size={16} />
      </span>
      <input
        type="password"
        placeholder={placeholder}
        value={value}
        autoComplete="new-password"
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-transparent py-3 text-sm text-text placeholder:text-muted/70 focus:outline-none"
      />
    </div>
  );
}

export default function ResetPage() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      {/* ambient parıltı — giriş ekranı ilə eyni imza */}
      <div className="pointer-events-none absolute top-1/4 h-96 w-96 rounded-full bg-accent/10 blur-[130px]" />

      <div className="absolute right-5 top-5 z-50">
        <LanguageSwitcher />
      </div>

      <Suspense fallback={<div className="min-h-screen" />}>
        <ResetForm />
      </Suspense>

      {/* terminal imzası — alt ticker */}
      <div className="absolute inset-x-0 bottom-0">
        <Ticker />
      </div>
    </div>
  );
}
