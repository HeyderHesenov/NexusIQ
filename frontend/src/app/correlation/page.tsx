"use client";

import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import {
  getCorrelationMatrix,
  getCorrelationPair,
  getCorrelationExplain,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { CorrelationMatrix } from "@/components/correlation/CorrelationMatrix";
import { CorrelationFocus } from "@/components/correlation/CorrelationFocus";
import { PairChart } from "@/components/correlation/PairChart";
import type { CorrMatrix, CorrPair } from "@/types";

const WINDOWS = [30, 90, 180, 365];

export default function CorrelationPage() {
  const { t, lang } = useI18n();
  const [window, setWindow] = useState(90);
  const [matrix, setMatrix] = useState<CorrMatrix | null>(null);
  const [mStatus, setMStatus] = useState<"loading" | "ready" | "error">("loading");
  const [view, setView] = useState<"bars" | "grid">("bars");
  const [focus, setFocus] = useState("btc");
  const [sel, setSel] = useState<{ a: string; b: string }>({ a: "btc", b: "spx" });
  const [pair, setPair] = useState<CorrPair | null>(null);
  const [pStatus, setPStatus] = useState<"loading" | "ready" | "error">("loading");
  const [explain, setExplain] = useState<string | null>(null);
  const [eStatus, setEStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    setMStatus("loading");
    getCorrelationMatrix(window).then((d) => {
      setMatrix(d);
      setMStatus(d && d.matrix.length ? "ready" : "error");
    });
  }, [window]);

  // Qrafik datası — sürətli, AI gözləmir.
  useEffect(() => {
    let active = true;
    setPStatus("loading");
    getCorrelationPair(sel.a, sel.b, window).then((d) => {
      if (!active) return;
      setPair(d);
      setPStatus(d ? "ready" : "error");
    });
    return () => {
      active = false;
    };
  }, [sel, window]);

  // AI izahı — ayrıca yüklənir, qrafiki bloklamır.
  useEffect(() => {
    let active = true;
    setExplain(null);
    setEStatus("loading");
    getCorrelationExplain(sel.a, sel.b, window, lang).then((text) => {
      if (!active) return;
      setExplain(text);
      setEStatus(text ? "ready" : "error");
    });
    return () => {
      active = false;
    };
  }, [sel, window, lang]);

  function selectPair(a: string, b: string) {
    if (a === b) return;
    setSel({ a, b });
  }

  const val = pair?.value ?? 0;
  const valColor =
    val >= 0.1 ? "text-up" : val <= -0.1 ? "text-down" : "text-muted";

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />

      <main className="mx-auto w-full max-w-7xl px-5 py-8 flex-1">
        <div className="mb-3 flex items-center gap-2">
          <Activity size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("corr.title")}
          </h1>
        </div>
        <p className="max-w-2xl text-sm text-muted">{t("corr.subtitle")}</p>

        {/* pəncərə seçimi */}
        <div className="mt-5 flex items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-wider text-muted">
            {t("corr.window")}
          </span>
          <div className="flex gap-1 rounded-xl border border-border bg-surface p-1">
            {WINDOWS.map((w) => (
              <button
                key={w}
                onClick={() => setWindow(w)}
                className={`rounded-lg px-3 py-1 text-sm font-medium transition-all ${
                  window === w
                    ? "bg-accent text-black"
                    : "text-muted hover:text-text"
                }`}
              >
                {w}{t("corr.days")}
              </button>
            ))}
          </div>
        </div>

        {/* korrelyasiya — fokus sıralaması (əsas) / şəbəkə (toggle) */}
        <section className="mt-6 rounded-card border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">
              {view === "bars" ? t("corr.ranked") : t("corr.matrix")}
            </h2>
            <div className="flex gap-1 rounded-lg border border-border bg-bg/40 p-0.5">
              {(["bars", "grid"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                    view === v
                      ? "bg-accent text-black"
                      : "text-muted hover:text-text"
                  }`}
                >
                  {v === "bars" ? t("corr.barView") : t("corr.gridView")}
                </button>
              ))}
            </div>
          </div>

          {mStatus === "loading" && (
            <div className="h-64 animate-pulse rounded-lg bg-surface-hover" />
          )}
          {mStatus === "error" && (
            <p className="py-12 text-center text-sm text-muted">{t("corr.error")}</p>
          )}
          {mStatus === "ready" && matrix && view === "bars" && (
            <CorrelationFocus
              data={matrix}
              focus={focus}
              selected={sel}
              onFocus={setFocus}
              onSelect={selectPair}
            />
          )}
          {mStatus === "ready" && matrix && view === "grid" && (
            <>
              <CorrelationMatrix data={matrix} selected={sel} onSelect={selectPair} />
              <p className="mt-4 flex flex-wrap items-center gap-3 text-[11px] text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: "rgba(34,197,94,0.85)" }} />
                  {t("corr.positive")}
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: "rgba(239,68,68,0.85)" }} />
                  {t("corr.negative")}
                </span>
                <span>{t("corr.clickHint")}</span>
              </p>
            </>
          )}
        </section>

        {/* cüt analizi */}
        <section className="mt-6 rounded-card border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">
              {pair ? `${pair.a.label} · ${pair.b.label}` : t("corr.pair")}
            </h2>
            {pStatus === "ready" && pair && (
              <span className={`font-mono text-lg font-semibold ${valColor}`}>
                {pair.value >= 0 ? "+" : ""}
                {pair.value.toFixed(2)}
              </span>
            )}
          </div>

          {pStatus === "loading" && (
            <div className="h-72 animate-pulse rounded-lg bg-surface-hover" />
          )}
          {pStatus === "error" && (
            <p className="py-12 text-center text-sm text-muted">{t("corr.pairError")}</p>
          )}
          {pStatus === "ready" && pair && (
            <>
              <PairChart
                series={pair.series}
                labelA={pair.a.label}
                labelB={pair.b.label}
              />
              {eStatus !== "error" && (
                <div className="mt-5 rounded-lg border border-border bg-bg/40 p-4">
                  <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-accent">
                    {t("corr.aiNote")}
                  </p>
                  {eStatus === "loading" ? (
                    <div className="space-y-2">
                      <div className="skeleton h-3.5 w-full rounded" />
                      <div className="skeleton h-3.5 w-4/5 rounded" />
                    </div>
                  ) : (
                    <p className="text-sm leading-relaxed text-text">{explain}</p>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
