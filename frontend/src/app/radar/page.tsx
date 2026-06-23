"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Radar } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { Sparkline } from "@/components/charts/Sparkline";
import { ScoreBars, ScoreRing, themeLabel } from "@/components/radar/RadarVisuals";
import { getRadar } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { RadarCategory, RadarItem } from "@/types";

const TABS: { key: RadarCategory; labelKey: string }[] = [
  { key: "crypto", labelKey: "radar.tab.crypto" },
  { key: "stock", labelKey: "radar.tab.stock" },
  { key: "commodity", labelKey: "radar.tab.commodity" },
];

function RadarCard({ item, rank }: { item: RadarItem; rank: number }) {
  const { t } = useI18n();
  const tag = item.type === "crypto" ? item.category : item.theme && themeLabel(item.theme);

  return (
    <Link
      href={`/radar/${item.key}`}
      className="group block rounded-card border border-border bg-surface p-4 transition-colors hover:bg-surface-hover sm:p-5"
    >
      <div className="flex items-center gap-3 sm:gap-4">
        <span className="hidden w-5 text-center font-mono text-sm text-muted tabular-nums sm:block">
          {rank}
        </span>
        <ScoreRing score={item.score} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-semibold group-hover:text-accent">{item.label}</span>
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
          <div className={`font-mono text-xs tabular-nums ${item.up ? "text-up" : "text-down"}`}>
            {item.chg}
          </div>
          <div className="mt-0.5 hidden sm:block">
            <Sparkline values={item.spark} width={96} height={28} />
          </div>
        </div>

        <ChevronRight
          size={18}
          className="hidden shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent sm:block"
        />
      </div>

      <div className="mt-4">
        <ScoreBars breakdown={item.breakdown} />
      </div>
    </Link>
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
