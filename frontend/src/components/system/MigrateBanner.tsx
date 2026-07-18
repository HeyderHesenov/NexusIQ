"use client";

/**
 * Birdəfəlik köçürmə banneri — real hesab girişindən sonra brauzerdə qalmış köhnə
 * localStorage datasını (`nexusiq_*`) serverə köçürməyi təklif edir.
 *
 * Görünmə şərti: authed VƏ hansısa köhnə açar mövcuddur VƏ `nexusiq_migrated_v1`
 * cari userId ilə uyğun DEYİL. İki terminal seçim (Köçür/Sil) həm köhnə açarları
 * silir, həm də `nexusiq_migrated_v1 = userId` yazır → paylaşılan brauzerdə
 * növbəti istifadəçiyə heç vaxt başqasının datası təklif olunmur. "Sonra" isə
 * yalnız bu sessiya üçün gizlədir.
 */
import { useEffect, useState } from "react";
import { ArrowRight, Trash2, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { apiPost } from "@/lib/api";
import { hydrateUserData } from "@/lib/user-sync";
import { KEY as WATCH_KEY } from "@/lib/watchlist";
import { KEY as HOLD_KEY } from "@/lib/holdings";
import { KEY as BM_KEY } from "@/lib/bookmarks";
import { KEY as ALERT_KEY } from "@/lib/alerts";
import { KEY as SAVED_KEY, eventKeyOf } from "@/lib/savedEvents";
import { KEY as LASTSEEN_KEY } from "@/lib/lastSeen";

const MIGRATED_KEY = "nexusiq_migrated_v1";
const SESSION_DISMISS = "nexusiq_migrate_dismissed";
const LEGACY_KEYS = [WATCH_KEY, HOLD_KEY, BM_KEY, ALERT_KEY, SAVED_KEY];

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function hasLegacy(): boolean {
  try {
    return LEGACY_KEYS.some((k) => localStorage.getItem(k) !== null);
  } catch {
    return false;
  }
}

/** Köhnə açarları /me/import gövdəsinə çevirir. */
function buildImport() {
  const watchlist = readJson<string[]>(WATCH_KEY, []);

  const holdMap = readJson<Record<string, { qty?: number; avgCost?: number }>>(
    HOLD_KEY,
    {},
  );
  const holdings = Object.entries(holdMap)
    .filter(([, h]) => typeof h?.qty === "number" && h.qty > 0)
    .map(([key, h]) => ({ key, qty: h.qty, avgCost: h.avgCost ?? 0 }));

  const bmMap = readJson<Record<string, unknown>>(BM_KEY, {});
  const bookmarks = Object.keys(bmMap)
    .map((id) => Number(id))
    .filter((n) => Number.isFinite(n));

  const alertList = readJson<
    { key: string; label?: string; direction: string; price: number }[]
  >(ALERT_KEY, []);
  const alerts = alertList
    .filter((a) => a && a.key && (a.direction === "above" || a.direction === "below"))
    .map((a) => ({
      assetKey: a.key,
      label: a.label,
      direction: a.direction,
      price: a.price,
    }));

  const savedMap = readJson<
    Record<string, { name?: string; badge?: string; sub?: string; href?: string }>
  >(SAVED_KEY, {});
  const savedEvents = Object.entries(savedMap)
    .filter(
      ([, v]) =>
        typeof v?.href === "string" &&
        v.href.startsWith("/") &&
        !v.href.startsWith("//"),
    )
    .map(([id, v]) => ({
      eventKey: eventKeyOf(id),
      payload: {
        title: (v.name ?? "").slice(0, 300),
        href: v.href as string,
        country: v.badge ? v.badge.slice(0, 8) : undefined,
        date: v.sub ? v.sub.slice(0, 40) : undefined,
      },
    }));

  return { watchlist, holdings, bookmarks, alerts, savedEvents };
}

function clearLegacy(): void {
  try {
    [...LEGACY_KEYS, LASTSEEN_KEY].forEach((k) => localStorage.removeItem(k));
  } catch {
    /* localStorage əlçatmaz */
  }
}

export function MigrateBanner() {
  const { user, status } = useAuth();
  const { t } = useI18n();
  const [phase, setPhase] = useState<"hidden" | "prompt" | "done">("hidden");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status !== "authed" || !user) {
      setPhase("hidden");
      return;
    }
    try {
      if (sessionStorage.getItem(SESSION_DISMISS) === "1") return;
      if (localStorage.getItem(MIGRATED_KEY) === user.id) return;
      if (hasLegacy()) setPhase("prompt");
    } catch {
      /* storage əlçatmaz — banner göstərmə */
    }
  }, [status, user]);

  if (phase === "hidden" || !user) return null;

  function seal(): void {
    clearLegacy();
    try {
      localStorage.setItem(MIGRATED_KEY, user!.id);
    } catch {
      /* localStorage əlçatmaz */
    }
  }

  async function doImport(): Promise<void> {
    if (busy) return;
    setBusy(true);
    try {
      await apiPost("/me/import", buildImport());
    } catch {
      setBusy(false); // banner qalır → yenidən cəhd
      return;
    }
    seal();
    hydrateUserData(); // serverdən təzə yüklə → UI dolur
    setBusy(false);
    setPhase("done");
    window.setTimeout(() => setPhase("hidden"), 2500);
  }

  function doDelete(): void {
    if (busy) return;
    if (!window.confirm(`${t("migrate.delete")}?`)) return;
    seal();
    setPhase("hidden");
  }

  function later(): void {
    try {
      sessionStorage.setItem(SESSION_DISMISS, "1");
    } catch {
      /* sessionStorage əlçatmaz */
    }
    setPhase("hidden");
  }

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label={t("migrate.prompt")}
      className="fade-up fixed inset-x-3 bottom-3 z-[90] mx-auto max-w-lg rounded-card border border-border bg-surface p-4 shadow-[var(--shadow)] sm:inset-x-auto sm:right-4"
    >
      {phase === "done" ? (
        <p className="py-1 text-center text-sm font-medium text-accent">
          {t("migrate.done")}
        </p>
      ) : (
        <>
          <div className="mb-3 flex items-start gap-2">
            <p className="text-sm leading-snug text-text">{t("migrate.prompt")}</p>
            <button
              onClick={later}
              aria-label={t("migrate.later")}
              className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-muted transition-colors hover:text-text"
            >
              <X size={15} />
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={doImport}
              disabled={busy}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-lg bg-accent px-3.5 py-2 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {t("migrate.import")}
              <ArrowRight size={15} />
            </button>
            <button
              onClick={doDelete}
              disabled={busy}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:border-down/50 hover:text-down disabled:opacity-60"
            >
              <Trash2 size={15} />
              {t("migrate.delete")}
            </button>
            <button
              onClick={later}
              disabled={busy}
              className="inline-flex min-h-[36px] items-center rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:text-text disabled:opacity-60"
            >
              {t("migrate.later")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
