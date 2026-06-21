"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Activity } from "lucide-react";
import { getCorrelationMatrix, getCorrelationPair } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { CorrelationMatrix } from "@/components/correlation/CorrelationMatrix";
import { PairChart } from "@/components/correlation/PairChart";
import type { CorrMatrix, CorrPair } from "@/types";

const WINDOWS = [30, 90, 180, 365];

export default function CorrelationPage() {
  const { t, lang } = useI18n();
  const [window, setWindow] = useState(90);
  const [matrix, setMatrix] = useState<CorrMatrix | null>(null);
  const [mStatus, setMStatus] = useState<"loading" | "ready" | "error">("loading");
  const [sel, setSel] = useState<{ a: string; b: string }>({ a: "btc", b: "spx" });
  const [pair, setPair] = useState<CorrPair | null>(null);
  const [pStatus, setPStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    setMStatus("loading");
    getCorrelationMatrix(window).then((d) => {
      setMatrix(d);
      setMStatus(d && d.matrix.length ? "ready" : "error");
    });
  }, [window]);

  const loadPair = useCallback(
    (a: string, b: string, w: number) => {
      setPStatus("loading");
      getCorrelationPair(a, b, w, lang).then((d) => {
        setPair(d);
        setPStatus(d ? "ready" : "error");
      });
    },
    [lang],
  );

  useEffect(() => {
    loadPair(sel.a, sel.b, window);
  }, [sel, window, loadPair]);

  function selectPair(a: string, b: string) {
    if (a === b) return;
    setSel({ a, b });
  }

  const val = pair?.value ?? 0;
  const valColor =
    val >= 0.1 ? "text-up" : val <= -0.1 ? "text-down" : "text-muted";

  return (
    <div className="min-h-screen">
      {/* üst panel */}
      <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-5">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-colors hover:border-accent hover:text-text"
          >
            <ArrowLeft size={15} />
            {t("news.back")}
          </Link>
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-accent" />
            <span className="text-lg font-semibold tracking-tight">
              {t("corr.title")}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8">
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

        {/* matris */}
        <section className="mt-6 rounded-card border border-border bg-surface p-5">
          <h2 className="mb-4 text-sm font-semibold">{t("corr.matrix")}</h2>
          {mStatus === "loading" && (
            <div className="h-64 animate-pulse rounded-lg bg-surface-hover" />
          )}
          {mStatus === "error" && (
            <p className="py-12 text-center text-sm text-muted">{t("corr.error")}</p>
          )}
          {mStatus === "ready" && matrix && (
            <CorrelationMatrix data={matrix} selected={sel} onSelect={selectPair} />
          )}
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
              {pair.explanation && (
                <div className="mt-5 rounded-lg border border-border bg-bg/40 p-4">
                  <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-accent">
                    {t("corr.aiNote")}
                  </p>
                  <p className="text-sm leading-relaxed text-text">
                    {pair.explanation}
                  </p>
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}
