"use client";

import { ArrowRight, Sparkles, Newspaper, Activity } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { Ticker } from "@/components/market/Ticker";

/**
 * Live pulse line — periodik (təkrarlanan) qiymət xətti.
 * y(0) === y(M) olduğu üçün iki eyni tile yan-yana qoyulanda
 * axın qırılmadan sonsuz dövr edir.
 */
const M = 120;
const W = 1000;
const MID = 172;

function yAt(i: number): number {
  const a = (k: number) => (Math.PI * 2 * k * i) / M;
  let y =
    MID +
    46 * Math.sin(a(1)) +
    22 * Math.sin(a(2) + 1.1) +
    13 * Math.sin(a(3) + 2.3) +
    7 * Math.sin(a(5) + 0.7);
  // heart-monitor spike-ləri (periodik, kəskin)
  y -= 46 * Math.pow(Math.max(0, Math.sin(a(2) + 0.5)), 16);
  return Math.max(58, Math.min(300, y));
}

const LINE = (() => {
  let d = "";
  for (let i = 0; i <= M; i++) {
    const x = (i / M) * W;
    const y = yAt(i);
    d += (i === 0 ? "M" : " L") + x.toFixed(1) + "," + y.toFixed(1);
  }
  return d;
})();
const AREA = `${LINE} L${W},320 L0,320 Z`;

/** Tək təkrar bloku (tile) — eyni xətt + sahə doluşu. */
function ChartTile() {
  return (
    <svg
      className="h-full w-1/2 shrink-0"
      viewBox="0 0 1000 320"
      preserveAspectRatio="none"
      aria-hidden
    >
      <defs>
        <linearGradient id="plArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.26" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={AREA} fill="url(#plArea)" />
      <path
        d={LINE}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
        style={{ filter: "drop-shadow(0 0 6px rgba(255,122,26,0.45))" }}
      />
    </svg>
  );
}

export function IntroSplash({ onEnter }: { onEnter: () => void }) {
  const { t } = useI18n();

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      {/* solğun grid fonu */}
      <div
        className="mb-grid pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          opacity: 0.1,
          maskImage:
            "radial-gradient(ellipse 75% 65% at 50% 42%, #000 28%, transparent 78%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 75% 65% at 50% 42%, #000 28%, transparent 78%)",
        }}
      />

      {/* sonsuz axan pulse line — alt tərəfdə (yazılardan aşağıda) */}
      <div className="mb-area pointer-events-none absolute inset-x-0 bottom-0 h-[34vh] overflow-hidden">
        <div className="pulse-line-track flex h-full w-[200%]">
          <ChartTile />
          <ChartTile />
        </div>
      </div>

      {/* alt qaraltma — wordmark oxunaqlı qalsın */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-transparent via-bg/40 to-bg/80" />

      {/* market lenti — yuxarıda, geniş, bütün pairlər axır */}
      <div className="absolute inset-x-0 top-6 z-10 flex justify-center px-4">
        <div className="w-full max-w-3xl fade-up">
          <Ticker compact />
        </div>
      </div>

      {/* mərkəz məzmun — yuxarıdan aşağı bir blok kimi gəlir */}
      <div className="mb-enter relative z-10 flex w-full flex-col items-center text-center">
        {/* wordmark */}
        <h1 className="text-7xl font-semibold tracking-tight sm:text-8xl">
          Nexus<span className="text-accent">FX</span>
        </h1>

        {/* narıncı alt xətt */}
        <div className="mt-4 h-[3px] w-64 rounded-full bg-gradient-to-r from-accent to-transparent" />

        {/* eyebrow */}
        <p className="mt-7 font-mono text-sm uppercase tracking-[0.38em] text-accent">
          Financial Intelligence Terminal
        </p>

        {/* CTA — avtomatik keçid yox, yalnız klik */}
        <button
          onClick={onEnter}
          className="mb-cta group mt-11 inline-flex items-center gap-3 rounded-xl border border-accent/40 bg-accent/5 px-9 py-4 text-base font-semibold text-text backdrop-blur transition-all duration-300 ease-out hover:-translate-y-0.5 hover:border-accent hover:bg-accent/10"
        >
          {t("intro.cta")}
          <ArrowRight
            size={18}
            className="text-accent transition-transform duration-300 ease-out group-hover:translate-x-1"
          />
        </button>

        {/* qabiliyyət chip-ləri */}
        <div
          className="fade-up mt-11 flex flex-wrap items-center justify-center gap-3"
          style={{ animationDelay: "1.7s" }}
        >
          {[
            { icon: <Sparkles size={15} />, key: "intro.feat1" },
            { icon: <Newspaper size={15} />, key: "intro.feat2" },
            { icon: <Activity size={15} />, key: "intro.feat3" },
          ].map((f) => (
            <span
              key={f.key}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/60 px-4 py-2 text-[15px] text-muted backdrop-blur transition-colors duration-200 hover:border-accent/50 hover:text-text"
            >
              <span className="text-accent">{f.icon}</span>
              {t(f.key)}
            </span>
          ))}
        </div>

        {/* stats sətri */}
        <p
          className="fade-up mt-7 font-mono text-sm tracking-wide text-muted"
          style={{ animationDelay: "1.9s" }}
        >
          {t("intro.stats")}
        </p>
      </div>
    </div>
  );
}
