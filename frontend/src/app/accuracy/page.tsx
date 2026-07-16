"use client";

import { useEffect, useState } from "react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { getAccuracy } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AccuracyCard, AccuracySlice } from "@/types";

const BY_TABS = ["category", "asset", "direction", "horizon"] as const;
const HORIZONS = [1, 5, 30] as const;

export default function AccuracyPage() {
  const { t } = useI18n();
  const [by, setBy] = useState<(typeof BY_TABS)[number]>("category");
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>(5);
  const [data, setData] = useState<AccuracyCard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getAccuracy(by, horizon).then((d) => {
      if (!alive) return;
      setData(d);
      setLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [by, horizon]);

  const slices = data?.slices ?? [];
  const sufficient = slices.filter((s) => !s.insufficient);
  const collecting = slices.filter((s) => s.insufficient);

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell flex-1 py-8">
        <div className="mb-6 max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
            {t("acc.eyebrow")}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{t("acc.title")}</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">{t("acc.subtitle")}</p>
        </div>

        {/* Kontrol: nəyə görə + üfüq */}
        <div className="mb-6 flex flex-wrap items-center gap-4">
          <div className="flex flex-wrap gap-1.5">
            {BY_TABS.map((b) => (
              <button
                key={b}
                onClick={() => setBy(b)}
                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                  by === b
                    ? "border-accent bg-accent text-black"
                    : "border-border bg-surface text-muted hover:border-accent hover:text-text"
                }`}
              >
                {t(`acc.by_${b}`)}
              </button>
            ))}
          </div>
          {by !== "horizon" && (
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[11px] uppercase tracking-wider text-muted">
                {t("acc.horizon")}
              </span>
              {HORIZONS.map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizon(h)}
                  className={`rounded-md border px-2.5 py-1 font-mono text-xs transition-colors ${
                    horizon === h
                      ? "border-accent text-accent"
                      : "border-border text-muted hover:text-text"
                  }`}
                >
                  +{h}
                  {t("acc.day")}
                </button>
              ))}
            </div>
          )}
        </div>

        {loading ? (
          <div className="space-y-2.5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-card bg-surface-hover" />
            ))}
          </div>
        ) : sufficient.length === 0 && collecting.length === 0 ? (
          <EmptyCard t={t} />
        ) : (
          <>
            {sufficient.length > 0 && (
              <div className="space-y-2.5">
                {sufficient.map((s) => (
                  <SliceRow key={s.key + s.horizon} s={s} by={by} t={t} />
                ))}
              </div>
            )}

            {collecting.length > 0 && (
              <div className="mt-6">
                <p className="mb-2.5 font-mono text-[11px] uppercase tracking-wider text-muted">
                  {t("acc.collecting")} · {t("acc.collectingHint")}
                </p>
                <div className="flex flex-wrap gap-2">
                  {collecting.map((s) => (
                    <span
                      key={s.key + s.horizon}
                      className="rounded-lg border border-dashed border-border px-3 py-1.5 text-sm text-muted"
                    >
                      {sliceLabel(by, s, t)}{" "}
                      <span className="font-mono text-[11px] text-muted/70">
                        (n={s.n})
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}

function sliceLabel(by: string, s: AccuracySlice, t: (k: string) => string): string {
  if (by === "category") {
    const l = t(`tab.${s.key}`);
    return l.startsWith("tab.") ? s.label : l;
  }
  if (by === "direction") {
    if (s.key === "up") return t("acc.dirUp");
    if (s.key === "down") return t("acc.dirDown");
  }
  return s.label;
}

/** Bir slice — hitRate barı + naiv baza markeri + delta çipi (dürüst müqayisə). */
function SliceRow({
  s,
  by,
  t,
}: {
  s: AccuracySlice;
  by: string;
  t: (k: string) => string;
}) {
  const hit = Math.round(s.hitRate * 100);
  const base = Math.round(s.baseRate * 100);
  const deltaPts = Math.round(s.delta * 100);
  const good = s.delta >= 0;

  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-text">{sliceLabel(by, s, t)}</span>
        <div className="flex items-center gap-3">
          <span className={`font-mono text-lg font-semibold ${good ? "text-up" : "text-down"}`}>
            {hit}%
          </span>
          <span
            className={`rounded-md border px-1.5 py-0.5 font-mono text-[11px] ${
              good ? "border-up/40 text-up" : "border-down/40 text-down"
            }`}
            title={t("acc.vsBase")}
          >
            {good ? "+" : ""}
            {deltaPts}pt {t("acc.vsBase")}
          </span>
        </div>
      </div>

      {/* hitRate barı + baza markeri */}
      <div className="relative h-2.5 overflow-hidden rounded-full bg-surface-hover">
        <div
          className={`h-full rounded-full ${good ? "bg-up" : "bg-down"}`}
          style={{ width: `${hit}%` }}
        />
        {/* naiv baza ("həmişə ▲") — dikey marker */}
        <div
          className="absolute top-[-2px] bottom-[-2px] w-0.5 bg-text/70"
          style={{ left: `${base}%` }}
          title={`${t("acc.baseRate")} ${base}%`}
        />
      </div>
      <div className="mt-1.5 flex items-center justify-between font-mono text-[11px] text-muted">
        <span>
          {t("acc.baseRate")}: {base}% · n={s.n}
        </span>
        <span>
          +{s.horizon}
          {t("acc.day")}
        </span>
      </div>
    </div>
  );
}

function EmptyCard({ t }: { t: (k: string) => string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border py-20 text-center">
      <p className="text-base font-medium text-text">{t("acc.collecting")}</p>
      <p className="mt-1.5 max-w-md text-sm text-muted">{t("acc.emptyHint")}</p>
    </div>
  );
}
