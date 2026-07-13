"use client";

import { useEffect, useState } from "react";
import { GitCompare, X } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { LineChart, SERIES_COLORS } from "@/components/charts/LineChart";
import { AssetPicker } from "@/components/assets/AssetPicker";
import { getAssets, getAssetDetail } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Asset, AssetDetail } from "@/types";

const RANGES = ["1mo", "3mo", "6mo", "1y"];
const MAX = 5;

export default function ComparePage() {
  const { t } = useI18n();
  const [registry, setRegistry] = useState<Asset[]>([]);
  const [selected, setSelected] = useState<string[]>(["btc", "spx"]);
  const [range, setRange] = useState("3mo");
  const [details, setDetails] = useState<Record<string, AssetDetail>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAssets().then(setRegistry);
  }, []);

  useEffect(() => {
    let stop = false;
    setLoading(true);
    Promise.all(selected.map((k) => getAssetDetail(k, range))).then((res) => {
      if (stop) return;
      const map: Record<string, AssetDetail> = {};
      selected.forEach((k, i) => {
        const d = res[i];
        if (d) map[k] = d;
      });
      setDetails(map);
      setLoading(false);
    });
    return () => {
      stop = true;
    };
  }, [selected, range]);

  function toggle(key: string) {
    setSelected((cur) =>
      cur.includes(key)
        ? cur.filter((k) => k !== key)
        : cur.length < MAX
          ? [...cur, key]
          : cur,
    );
  }

  const series = selected
    .map((k, i) => {
      const h = details[k]?.history;
      if (!h || h.points.length < 2) return null;
      return {
        label: h.label,
        color: SERIES_COLORS[i % SERIES_COLORS.length],
        points: h.points.map((p) => ({ date: p.date, value: p.close })),
      };
    })
    .filter(Boolean) as { label: string; color: string; points: { date: string; value: number }[] }[];

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell py-8 flex-1">
        <div className="mb-2 flex items-center gap-2">
          <GitCompare size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("nav.compare")}
          </h1>
        </div>
        <p className="mb-5 text-sm text-muted">{t("compare.subtitle")}</p>

        {/* seçilmiş aktivlər — rəngli pill-lər */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {selected.map((k, i) => {
            const label = registry.find((a) => a.key === k)?.label ?? k;
            return (
              <span
                key={k}
                className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm"
              >
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }}
                />
                {label}
                <button
                  onClick={() => toggle(k)}
                  className="text-muted transition-colors hover:text-down"
                  aria-label="sil"
                >
                  <X size={14} />
                </button>
              </span>
            );
          })}
          <span className="font-mono text-xs text-muted">
            {selected.length}/{MAX}
          </span>
        </div>

        {/* aktiv seçici */}
        <div className="mb-5">
          <AssetPicker
            assets={registry}
            isSelected={(k) => selected.includes(k)}
            onToggle={toggle}
            disableUnselected={selected.length >= MAX}
          />
        </div>

        {/* dövr */}
        <div className="mb-5 flex gap-1 rounded-xl border border-border bg-surface p-1 w-fit">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded-lg px-3 py-1 text-sm font-medium transition-all ${
                range === r ? "bg-accent text-black" : "text-muted hover:text-text"
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        {/* normallaşdırılmış qrafik — səhifənin əsas elementi */}
        <section className="relative rounded-card border border-border bg-surface p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-accent">
              {t("compare.normalized")}
            </p>
            <span className="flex items-center gap-2 font-mono text-xs text-muted">
              {loading && (
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent border-t-transparent" />
              )}
              {range}
            </span>
          </div>
          <div className={loading ? "opacity-50 transition-opacity" : "transition-opacity"}>
            <LineChart series={series} normalize height={460} />
          </div>
        </section>

        {/* cədvəl */}
        <section className="mt-5 overflow-hidden rounded-card border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface text-muted">
              <tr>
                <th className="px-4 py-2 text-left font-medium">{t("compare.asset")}</th>
                <th className="px-4 py-2 text-right font-medium">{t("compare.price")}</th>
                <th className="px-4 py-2 text-right font-medium">{t("compare.rangeChg")}</th>
              </tr>
            </thead>
            <tbody>
              {selected.map((k, i) => {
                const d = details[k];
                const q = d?.quote;
                const h = d?.history;
                const chg = h?.changePct ?? 0;
                return (
                  <tr key={k} className="border-t border-border">
                    <td className="px-4 py-2.5 font-medium">
                      <span className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-sm"
                          style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }}
                        />
                        {q?.label ?? k}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      {q?.val ?? "—"}
                    </td>
                    <td
                      className={`px-4 py-2.5 text-right font-mono ${chg >= 0 ? "text-up" : "text-down"}`}
                    >
                      {chg >= 0 ? "+" : ""}
                      {chg.toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      </main>
      <Footer />
    </div>
  );
}
