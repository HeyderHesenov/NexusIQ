"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Eye, RefreshCw } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { getAnomalies } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AnomalyScan, AnomalySeverity, NearMove } from "@/types";

// Şiddət rəngləri — istiqamətdən (yaşıl/qırmızı) ayrı semantik siqnal.
const SEV: Record<AnomalySeverity, { dot: string; ring: string; key: string }> = {
  medium: { dot: "#fbbf24", ring: "rgba(251,191,36,0.35)", key: "anom.sevMedium" },
  high: { dot: "#f97316", ring: "rgba(249,115,22,0.40)", key: "anom.sevHigh" },
  extreme: { dot: "#ef4444", ring: "rgba(239,68,68,0.45)", key: "anom.sevExtreme" },
};

/** Signature — σ sapma oxu. Mərkəz = normal (0), marker neçə σ kənarda. */
function DeviationGauge({ z, up }: { z: number; up: boolean }) {
  const clamped = Math.max(-6, Math.min(6, z));
  const pos = ((clamped + 6) / 12) * 100; // 0..100%
  const color = up ? "var(--up)" : "var(--down)";
  return (
    <div className="relative h-9 select-none">
      {/* ox xətti */}
      <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-border" />
      {/* ±3 anomaliya sərhədləri */}
      {[25, 75].map((p) => (
        <div
          key={p}
          className="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-border"
          style={{ left: `${p}%` }}
        />
      ))}
      {/* mərkəz (normal) */}
      <div className="absolute left-1/2 top-1/2 h-4 w-px -translate-x-1/2 -translate-y-1/2 bg-muted/60" />
      {/* sapma izi — mərkəzdən markerə */}
      <div
        className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
        style={{
          left: `${Math.min(50, pos)}%`,
          width: `${Math.abs(pos - 50)}%`,
          background: color,
          opacity: 0.5,
        }}
      />
      {/* marker */}
      <div
        className="absolute top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center justify-center"
        style={{ left: `${pos}%` }}
      >
        <span
          className="h-3 w-3 rounded-full ring-4"
          style={{ background: color, boxShadow: `0 0 0 1px var(--bg)` }}
        />
      </div>
      {/* z dəyəri */}
      <div
        className="absolute -bottom-0.5 -translate-x-1/2 font-mono text-[10px] text-muted"
        style={{ left: `${pos}%` }}
      >
        {z > 0 ? "+" : ""}
        {z.toFixed(1)}σ
      </div>
    </div>
  );
}

export default function AnomaliesPage() {
  const { t } = useI18n();
  const [scan, setScan] = useState<AnomalyScan | null>(null);
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [scanning, setScanning] = useState(false);

  const load = useCallback(async (refresh: boolean) => {
    if (refresh) setScanning(true);
    const data = await getAnomalies(refresh);
    setScan(data);
    setStatus("ready");
    setScanning(false);
  }, []);

  useEffect(() => {
    load(false);
  }, [load]);

  const rows = scan?.anomalies ?? [];
  const near = scan?.near ?? [];
  const stats = scan?.stats;
  const asof = scan?.asof ?? "";

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-4xl px-5 py-8">
        {/* başlıq */}
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <div className="mb-1.5 flex items-center gap-2">
              <Activity size={18} className="text-accent" />
              <h1 className="text-2xl font-semibold tracking-tight">
                {t("anom.title")}
              </h1>
            </div>
            {status === "ready" && (
              <p className="text-sm text-muted">
                {rows.length > 0 ? (
                  <>
                    <span className="font-mono font-semibold text-text">
                      {rows.length}
                    </span>{" "}
                    {t("anom.lead")}
                    {asof && (
                      <>
                        {" · "}
                        <span className="font-mono">{asof}</span>
                      </>
                    )}
                  </>
                ) : (
                  t("anom.calmSub")
                )}
              </p>
            )}
          </div>
          <button
            onClick={() => load(true)}
            disabled={scanning}
            className="flex shrink-0 items-center gap-2 rounded-xl border border-border bg-surface px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:text-accent disabled:opacity-60"
          >
            <RefreshCw size={14} className={scanning ? "animate-spin" : ""} />
            <span className="hidden sm:inline">
              {scanning ? t("anom.scanning") : t("anom.refresh")}
            </span>
          </button>
        </div>

        {/* stat zolağı — skan əhatəsi bir baxışda */}
        {status === "ready" && stats && (
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label={t("anom.statUniverse")} value={stats.universe} />
            <StatCard
              label={t("anom.statAnomalies")}
              value={stats.anomalies}
              accent={stats.anomalies > 0}
            />
            <StatCard label={t("anom.statWatch")} value={stats.near} />
            <StatCard label={t("anom.statAsof")} value={asof || "—"} mono />
          </div>
        )}

        {/* skeleton */}
        {status === "loading" && (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-24 animate-pulse rounded-card border border-border bg-surface"
              />
            ))}
          </div>
        )}

        {/* sakit hal */}
        {status === "ready" && rows.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-card border border-border bg-surface py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-border">
              <Activity size={22} className="text-up" />
            </div>
            <p className="text-lg font-semibold">{t("anom.calm")}</p>
            <p className="mt-1 max-w-xs text-sm text-muted">{t("anom.calmSub")}</p>
          </div>
        )}

        {/* siyahı */}
        {status === "ready" && rows.length > 0 && (
          <div className="space-y-3">
            {rows.map((a) => {
              const sev = SEV[a.severity];
              const up = a.change_pct >= 0;
              return (
                <div
                  key={a.key}
                  className="relative overflow-hidden rounded-card border border-border bg-surface transition-colors hover:bg-surface-hover"
                >
                  {/* sol şiddət zolağı */}
                  <span
                    className="absolute inset-y-0 left-0 w-1"
                    style={{ background: sev.dot }}
                  />
                  <div className="grid grid-cols-[1fr_auto] items-center gap-4 py-4 pl-5 pr-4 sm:grid-cols-[200px_1fr_120px]">
                    {/* aktiv */}
                    <div className="min-w-0">
                      <Link
                        href={`/asset/${a.key}`}
                        className="block truncate font-semibold hover:text-accent"
                      >
                        {a.label}
                      </Link>
                      <div className="mt-1 flex items-center gap-1.5">
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide"
                          style={{ background: sev.ring, color: sev.dot }}
                        >
                          <span
                            className="h-1.5 w-1.5 rounded-full"
                            style={{ background: sev.dot }}
                          />
                          {t(sev.key)}
                        </span>
                        <span className="text-[11px] text-muted">{a.type}</span>
                      </div>
                    </div>

                    {/* signature qauç — geniş ekranda ortada */}
                    <div className="order-3 col-span-2 mt-2 sm:order-none sm:col-span-1 sm:mt-0">
                      <DeviationGauge z={a.price_z} up={up} />
                    </div>

                    {/* hərəkət + həcm */}
                    <div className="text-right">
                      <div
                        className={`font-mono text-lg font-semibold ${
                          up ? "text-up" : "text-down"
                        }`}
                      >
                        {a.change_pct > 0 ? "+" : ""}
                        {a.change_pct.toFixed(2)}%
                      </div>
                      <div className="mt-0.5 font-mono text-[11px] text-muted">
                        vol z {a.volume_z.toFixed(1)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            <p className="pt-2 text-center text-[11px] text-muted">
              {t("anom.footnote")}
            </p>
          </div>
        )}

        {/* müşahidə altında — sub-həddi erkən siqnallar */}
        {status === "ready" && near.length > 0 && (
          <section className="mt-8">
            <div className="mb-1 flex items-center gap-2">
              <Eye size={16} className="text-accent" />
              <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
                {t("anom.watchTitle")}
              </h2>
            </div>
            <p className="mb-3 text-sm text-muted">{t("anom.watchSub")}</p>

            <div className="space-y-2">
              {near.map((n) => (
                <WatchRow key={n.key} n={n} />
              ))}
            </div>

            <p className="pt-3 text-center text-[11px] text-muted/70">
              {t("anom.watchFootnote")}
            </p>
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
}

/** Stat kartı — skan əhatəsi (powerlaw/brief üslubu ilə uyğun). */
function StatCard({
  label,
  value,
  accent,
  mono,
}: {
  label: string;
  value: number | string;
  accent?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="rounded-card border border-border bg-surface px-4 py-2.5">
      <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
        {label}
      </div>
      <div
        className={`mt-0.5 font-semibold tabular-nums ${
          mono ? "font-mono text-sm" : "font-mono text-lg"
        } ${accent ? "text-accent" : "text-text"}`}
      >
        {value}
      </div>
    </div>
  );
}

/** Müşahidə sətri — anomaliya kartının yüngül variantı (eyni σ-qauç). */
function WatchRow({ n }: { n: NearMove }) {
  const { t } = useI18n();
  const up = n.change_pct >= 0;
  return (
    <div className="rounded-card border border-border bg-surface transition-colors hover:bg-surface-hover">
      <div className="grid grid-cols-[1fr_auto] items-center gap-4 px-4 py-3 sm:grid-cols-[200px_1fr_120px]">
        <div className="min-w-0">
          <Link
            href={`/asset/${n.key}`}
            className="block truncate font-medium hover:text-accent"
          >
            {n.label}
          </Link>
          <span className="text-[11px] text-muted">{n.type}</span>
        </div>

        <div className="order-3 col-span-2 mt-1 sm:order-none sm:col-span-1 sm:mt-0">
          <DeviationGauge z={n.price_z} up={up} />
        </div>

        <div className="text-right">
          <div
            className={`font-mono text-base font-semibold ${
              up ? "text-up" : "text-down"
            }`}
          >
            {n.change_pct > 0 ? "+" : ""}
            {n.change_pct.toFixed(2)}%
          </div>
          <div className="mt-0.5 font-mono text-[11px] text-muted">
            vol z {n.volume_z.toFixed(1)}
          </div>
        </div>
      </div>
    </div>
  );
}
