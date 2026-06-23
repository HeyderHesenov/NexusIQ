"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Radar, Sparkles } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { Sparkline } from "@/components/charts/Sparkline";
import { getRadar, getRadarExplain } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { RadarCategory, RadarItem } from "@/types";

const TABS: { key: RadarCategory; labelKey: string }[] = [
  { key: "crypto", labelKey: "radar.tab.crypto" },
  { key: "stock", labelKey: "radar.tab.stock" },
  { key: "commodity", labelKey: "radar.tab.commodity" },
];

// Tema açarını oxunaqlı teqə çevir (ai_data → AI Data).
function themeLabel(theme: string): string {
  return theme
    .split("_")
    .map((w) => (w.length <= 3 ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1)))
    .join(" ");
}

// Bal səviyyəsinə görə rəng — yüksək=accent, orta=amber, aşağı=muted.
function tierColor(score: number): string {
  if (score >= 65) return "var(--accent)";
  if (score >= 45) return "#fbbf24";
  return "var(--muted)";
}

/** Signature — fürsət balı radial halqası (0..100). */
function ScoreRing({ score }: { score: number }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(100, score)) / 100);
  const color = tierColor(score);
  return (
    <div className="relative h-[68px] w-[68px] shrink-0">
      <svg width="68" height="68" viewBox="0 0 68 68" className="-rotate-90">
        <circle cx="34" cy="34" r={r} fill="none" stroke="var(--border)" strokeWidth="5" />
        <circle
          cx="34"
          cy="34"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-mono text-lg font-semibold tabular-nums" style={{ color }}>
          {Math.round(score)}
        </span>
      </div>
    </div>
  );
}

/** Bal komponentləri — hər biri stacked: etiket+dəyər üstdə, bar tam enli altda. */
function ScoreBars({ breakdown }: { breakdown: Record<string, number> }) {
  const { t } = useI18n();
  return (
    <div className="grid grid-cols-3 gap-x-3 gap-y-2 sm:gap-x-4">
      {Object.entries(breakdown).map(([key, v]) => {
        const color = tierColor(v);
        return (
          <div key={key}>
            <div className="flex items-baseline justify-between gap-1.5">
              <span className="truncate text-[10px] font-medium uppercase tracking-wide text-muted">
                {t(`radar.bd.${key}`)}
              </span>
              <span
                className="font-mono text-[11px] font-semibold tabular-nums"
                style={{ color }}
              >
                {Math.round(v)}
              </span>
            </div>
            <span className="mt-1.5 block h-1 overflow-hidden rounded-full bg-border">
              <span
                className="block h-full rounded-full motion-safe:transition-[width] motion-safe:duration-500"
                style={{ width: `${v}%`, background: color }}
              />
            </span>
          </div>
        );
      })}
    </div>
  );
}

function RadarCard({ item, rank }: { item: RadarItem; rank: number }) {
  const { t, lang } = useI18n();
  const [explain, setExplain] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [asked, setAsked] = useState(false);

  const onExplain = useCallback(async () => {
    setExplaining(true);
    setAsked(true);
    const text = await getRadarExplain(item.key, lang);
    setExplain(text);
    setExplaining(false);
  }, [item.key, lang]);

  const tag = item.type === "crypto" ? item.category : item.theme && themeLabel(item.theme);

  return (
    <div className="rounded-card border border-border bg-surface transition-colors hover:bg-surface-hover">
      <div className="p-4 sm:p-5">
        {/* üst sətir: sıra + halqa + ad/meta + qiymət */}
        <div className="flex items-center gap-3 sm:gap-4">
          <span className="hidden w-5 text-center font-mono text-sm text-muted tabular-nums sm:block">
            {rank}
          </span>
          <ScoreRing score={item.score} />

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-semibold hover:text-accent"
              >
                {item.label}
                <ExternalLink size={12} className="text-muted" />
              </a>
              {tag && (
                <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                  {tag}
                </span>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-[11px] text-muted">
              <span>
                {t("radar.mc")} <span className="text-text">{item.mcapFmt}</span>
              </span>
              {item.revenueFmt && (
                <span>
                  {t("radar.rev")} <span className="text-up">{item.revenueFmt}</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-end gap-1.5">
            <div className="font-mono text-sm font-semibold tabular-nums">{item.val}</div>
            <div
              className={`font-mono text-xs tabular-nums ${item.up ? "text-up" : "text-down"}`}
            >
              {item.chg}
            </div>
            <div className="mt-0.5 hidden sm:block">
              <Sparkline values={item.spark} width={96} height={28} />
            </div>
          </div>
        </div>

        {/* komponentlər — tam enli, rahat oxunan */}
        <div className="mt-4">
          <ScoreBars breakdown={item.breakdown} />
        </div>
      </div>

      {/* AI izah */}
      <div className="border-t border-border px-4 py-3 sm:px-5">
        {asked ? (
          <p className="flex items-start gap-2 text-sm text-text">
            <Sparkles size={14} className="mt-0.5 shrink-0 text-accent" />
            <span>
              {explaining ? t("radar.explaining") : explain || t("radar.noExplain")}
            </span>
          </p>
        ) : (
          <button
            onClick={onExplain}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-accent transition-opacity hover:opacity-80"
          >
            <Sparkles size={13} />
            {t("radar.explain")}
          </button>
        )}
      </div>
    </div>
  );
}

export default function RadarPage() {
  const { t } = useI18n();
  const [tab, setTab] = useState<RadarCategory>("crypto");
  const [rows, setRows] = useState<RadarItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready">("loading");

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getRadar(tab).then((data) => {
      if (cancelled) return;
      setRows(data);
      setStatus("ready");
    });
    return () => {
      cancelled = true;
    };
  }, [tab]);

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-4xl px-5 py-8">
        {/* başlıq */}
        <div className="mb-5">
          <div className="mb-1.5 flex items-center gap-2">
            <Radar size={18} className="text-accent" />
            <h1 className="text-2xl font-semibold tracking-tight">{t("radar.title")}</h1>
          </div>
          <p className="text-sm text-muted">{t("radar.subtitle")}</p>
        </div>

        {/* kateqoriya tabları */}
        <div className="mb-5 flex gap-1 rounded-xl border border-border bg-surface p-1">
          {TABS.map((tb) => (
            <button
              key={tb.key}
              onClick={() => setTab(tb.key)}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                tab === tb.key ? "bg-accent text-black" : "text-muted hover:text-text"
              }`}
            >
              {t(tb.labelKey)}
            </button>
          ))}
        </div>

        {/* skeleton */}
        {status === "loading" && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-32 animate-pulse rounded-card border border-border bg-surface"
              />
            ))}
          </div>
        )}

        {/* boş */}
        {status === "ready" && rows.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-card border border-border bg-surface py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-border">
              <Radar size={22} className="text-muted" />
            </div>
            <p className="text-sm text-muted">{t("radar.empty")}</p>
          </div>
        )}

        {/* siyahı */}
        {status === "ready" && rows.length > 0 && (
          <div className="space-y-3">
            {rows.map((item, i) => (
              <RadarCard key={item.key} item={item} rank={i + 1} />
            ))}
            <p className="pt-2 text-center text-[11px] text-muted">{t("radar.footnote")}</p>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
