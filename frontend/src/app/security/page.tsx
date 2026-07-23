"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  KeyRound,
  LogIn,
  LogOut,
  Monitor,
  ShieldCheck,
  Smartphone,
  Trash2,
  UserPlus,
  type LucideIcon,
} from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { useAuth } from "@/lib/auth-context";
import { listSessions, revokeSession, type Session } from "@/lib/auth";
import { listAudit, type AuditEvent } from "@/lib/audit";
import { useI18n } from "@/lib/i18n";
import { formatDateTime } from "@/lib/utils";

/** UA sətrindən oxunaqlı cihaz adı ("Chrome · macOS") + mobil/masaüstü. */
function describeDevice(ua: string | null): { name: string; mobile: boolean } | null {
  if (!ua) return null;
  const mobile = /mobile|iphone|ipad|android/i.test(ua);
  const browser = /edg/i.test(ua)
    ? "Edge"
    : /chrome|crios/i.test(ua)
      ? "Chrome"
      : /firefox|fxios/i.test(ua)
        ? "Firefox"
        : /safari/i.test(ua)
          ? "Safari"
          : null;
  const os = /windows/i.test(ua)
    ? "Windows"
    : /iphone|ipad|ios/i.test(ua)
      ? "iOS"
      : /mac os x|macintosh/i.test(ua)
        ? "macOS"
        : /android/i.test(ua)
          ? "Android"
          : /linux/i.test(ua)
            ? "Linux"
            : null;
  const parts = [browser, os].filter(Boolean);
  return { name: parts.length ? parts.join(" · ") : ua.slice(0, 40), mobile };
}

const EVENT_ICON: Record<string, LucideIcon> = {
  login_success: LogIn,
  google_login: LogIn,
  login_failure: AlertTriangle,
  login_locked: AlertTriangle,
  reuse_detected: AlertTriangle,
  register: UserPlus,
  register_blocked: AlertTriangle,
  logout: LogOut,
  logout_all: LogOut,
  session_revoke: Trash2,
  password_change: KeyRound,
  password_reset_request: KeyRound,
  password_reset_confirm: KeyRound,
};
const ALERT_EVENTS = new Set([
  "login_failure",
  "login_locked",
  "reuse_detected",
  "register_blocked",
]);

export default function SecurityPage() {
  const { t } = useI18n();
  const { logoutAll } = useAuth();
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [sessionsError, setSessionsError] = useState(false);
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);

  const loadSessions = useCallback(() => {
    setSessionsError(false);
    listSessions()
      .then(setSessions)
      .catch(() => {
        setSessions([]);
        setSessionsError(true);
      });
  }, []);

  useEffect(() => {
    loadSessions();
    listAudit()
      .then(setEvents)
      .catch(() => setEvents([]));
  }, [loadSessions]);

  async function revoke(sid: string) {
    setRevoking(sid);
    try {
      await revokeSession(sid);
      loadSessions();
    } finally {
      setRevoking(null);
    }
  }

  const others = (sessions ?? []).filter((s) => !s.current);

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell-narrow py-8 flex-1">
        <div className="mb-2 flex items-center gap-2">
          <ShieldCheck size={20} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("nav.security")}
          </h1>
        </div>
        <p className="mb-6 text-sm text-muted">{t("sessions.subtitle")}</p>

        {/* Cihazlar / sessiyalar */}
        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">{t("sessions.title")}</h2>
            {others.length > 0 && (
              <button
                onClick={logoutAll}
                className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-down hover:text-down"
              >
                <LogOut size={13} />
                {t("sessions.revokeAll")}
              </button>
            )}
          </div>

          {sessions === null ? (
            <div className="space-y-2">
              {[0, 1].map((i) => (
                <div
                  key={i}
                  className="h-[58px] animate-pulse rounded-lg border border-border bg-surface"
                />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <p className="rounded-card border border-dashed border-border py-10 text-center text-sm text-muted">
              {sessionsError ? t("sessions.loadError") : t("sessions.empty")}
            </p>
          ) : (
            <div className="space-y-2">
              {sessions.map((s) => {
                const dev = describeDevice(s.userAgent);
                const DeviceIcon = dev?.mobile ? Smartphone : Monitor;
                return (
                  <div
                    key={s.id}
                    className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
                      s.current
                        ? "border-accent-soft bg-accent-soft"
                        : "border-border bg-surface"
                    }`}
                  >
                    <DeviceIcon
                      size={18}
                      className={s.current ? "text-accent" : "text-muted"}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">
                          {dev?.name ?? t("sessions.unknownDevice")}
                        </span>
                        {s.current && (
                          <span className="shrink-0 rounded-full bg-accent px-2 py-0.5 text-[11px] font-semibold text-black">
                            {t("sessions.current")}
                          </span>
                        )}
                      </div>
                      <div className="mt-0.5 truncate font-mono text-xs text-muted">
                        {s.ip ?? "—"} · {t("sessions.lastUsed")}:{" "}
                        {formatDateTime(s.lastUsedAt) || "—"}
                      </div>
                    </div>
                    {!s.current && (
                      <button
                        onClick={() => revoke(s.id)}
                        disabled={revoking === s.id}
                        title={t("sessions.revoke")}
                        aria-label={t("sessions.revoke")}
                        className="shrink-0 text-muted transition-colors hover:text-down disabled:opacity-40"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Son fəaliyyət */}
        <section className="mt-8">
          <h2 className="mb-1 text-sm font-semibold">{t("audit.title")}</h2>
          <p className="mb-3 text-xs text-muted">{t("audit.subtitle")}</p>

          {events === null ? (
            <div className="space-y-1.5">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-11 animate-pulse rounded-lg border border-border bg-surface"
                />
              ))}
            </div>
          ) : events.length === 0 ? (
            <p className="rounded-card border border-dashed border-border py-10 text-center text-sm text-muted">
              {t("audit.empty")}
            </p>
          ) : (
            <ul className="overflow-hidden rounded-card border border-border bg-surface">
              {events.map((e) => {
                const Icon = EVENT_ICON[e.event] ?? ShieldCheck;
                const label = t(`audit.ev.${e.event}`);
                const alert = ALERT_EVENTS.has(e.event);
                return (
                  <li
                    key={e.id}
                    className="flex items-center gap-3 border-b border-border px-4 py-2.5 last:border-b-0"
                  >
                    <Icon
                      size={15}
                      className={alert ? "text-down" : "text-muted"}
                    />
                    <span className="flex-1 text-sm">
                      {label === `audit.ev.${e.event}` ? e.event : label}
                    </span>
                    <span className="shrink-0 font-mono text-xs text-muted">
                      {e.ip ? `${e.ip} · ` : ""}
                      {formatDateTime(e.createdAt)}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
