"use client";

import { useEffect, useState } from "react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { PowerLawChart } from "@/components/powerlaw/PowerLawChart";
import { AIAssistantFab } from "@/components/ai/AIAssistantFab";
import { getPowerLaw, getPowerLawAssets } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { PowerLaw } from "@/types";

function usd(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1000) return `$${Math.round(n).toLocaleString()}`;
  return `$${n.toFixed(2)}`;
}

export default function PowerLawPage() {
  const { t } = useI18n();
  const [assets, setAssets] = useState<{ key: string; label: string }[]>([]);
  const [asset, setAsset] = useState("btc");
  const [data, setData] = useState<PowerLaw | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getPowerLawAssets().then(setAssets);
  }, []);

  useEffect(() => {
    setStatus("loading");
    getPowerLaw(asset).then((d) => {
      setData(d);
      setStatus(d && d.series?.length ? "ready" : "error");
    });
  }, [asset]);

  const below = (data?.deviationPct ?? 0) < 0;
  const label = data?.label ?? asset.toUpperCase();

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-5xl px-5 py-8">
        {/* eyebrow */}
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-accent">
          {label} · {t("pl.title")}
        </p>

        {/* coin seçici — yalnız birdən çox aktiv olduqda */}
        {assets.length > 1 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {assets.map((a) => (
              <button
                key={a.key}
                onClick={() => setAsset(a.key)}
                className={`rounded-lg border px-3 py-1 text-sm font-medium transition-all ${
                  asset === a.key
                    ? "border-accent bg-accent text-black"
                    : "border-border bg-surface text-muted hover:text-text"
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
        )}

        {status === "loading" && (
          <div className="mt-6 h-96 animate-pulse rounded-card bg-surface-hover" />
        )}
        {status === "error" && (
          <p className="mt-10 text-center text-sm text-muted">{t("pl.error")}</p>
        )}

        {status === "ready" && data && (
          <>
            {/* thesis — verdict */}
            <h1 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
              {label} {t("pl.heroPre")}{" "}
              <span className={below ? "text-up" : "text-down"}>
                {Math.abs(data.deviationPct)}% {below ? t("pl.below") : t("pl.above")}
              </span>{" "}
              {t("pl.heroPost")}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              {t("pl.intro")}
            </p>

            {/* açar göstəricilər */}
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label={t("pl.price")} value={usd(data.price)} />
              <Stat label={t("pl.fair")} value={usd(data.model)} accent />
              <Stat label={t("pl.support")} value={usd(data.support)} />
              <Stat label={t("pl.resistance")} value={usd(data.resistance)} />
            </div>

            {/* qrafik */}
            <section className="mt-6 rounded-card border border-border bg-surface p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold">{t("pl.corridor")}</h2>
                <span className="font-mono text-xs text-muted">
                  R² {(data.r2 * 100).toFixed(1)}% · n={data.b}
                </span>
              </div>
              <PowerLawChart series={data.series} />
            </section>

            {/* proqnozlar */}
            <section className="mt-6">
              <h2 className="mb-3 text-sm font-semibold">{t("pl.projections")}</h2>
              <div className="overflow-hidden rounded-card border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-surface text-muted">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">{t("pl.horizon")}</th>
                      <th className="px-4 py-2 text-right font-medium">{t("pl.support")}</th>
                      <th className="px-4 py-2 text-right font-medium">{t("pl.fair")}</th>
                      <th className="px-4 py-2 text-right font-medium">{t("pl.resistance")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.projections.map((p) => (
                      <tr key={p.years} className="border-t border-border">
                        <td className="px-4 py-2.5 font-medium">
                          +{p.years} {t("pl.years")} · {p.date}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-muted">
                          {usd(p.support)}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-accent">
                          {usd(p.model)}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-muted">
                          {usd(p.resistance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* izah */}
            <section className="mt-8 rounded-card border border-border bg-surface p-5">
              <h2 className="mb-2 text-sm font-semibold">{t("pl.whatTitle")}</h2>
              <p className="text-sm leading-relaxed text-muted">{t("pl.what")}</p>
              <p className="mt-3 font-mono text-xs text-muted">
                log₁₀(price) = {data.a} + {data.b} · log₁₀(genesis-dən günlər)
              </p>
              <p className="mt-3 text-xs leading-relaxed text-muted/80">
                {t("pl.caveat")}
              </p>
            </section>
          </>
        )}
      </main>
      <AIAssistantFab />
      <Footer />
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
        {label}
      </p>
      <p
        className={`mt-1 font-mono text-lg font-semibold ${accent ? "text-accent" : "text-text"}`}
      >
        {value}
      </p>
    </div>
  );
}
