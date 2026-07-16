"use client";

import { memo } from "react";
import { Bitcoin, DollarSign, TrendingUp, Fuel, Newspaper } from "lucide-react";
import type { Category } from "@/types";

/**
 * Brendli redaksiya örtüyü — şəkli olmayan və ya yüklənməyən xəbərlər üçün.
 * Çoxqatlı qradiyent + seed-dən deterministik market-chart motivi + kateqoriya
 * qlifi + wordmark. Eyni xəbər → eyni örtük. Placeholder yox, real örtük hissi.
 *
 * `compact` — kiçik siyahı örtüyü (96×64, aktiv səhifəsi). Bu ölçüdə kimlik
 * QRADİYENT HUE + CHART MOTİVİDİR; etiket ("COMMODITIES" ≈95px > 96px qutu) və
 * wordmark oxunmur, 104px qlif isə qutudan enlidir — ona görə düşürlər.
 * Ölçülər tam qatda deyil, bu proplada tənzimlənir (qutunu dəyişmə).
 */
type Cfg = { hue: number; Icon: typeof Bitcoin; label: string };

const CFG: Record<string, Cfg> = {
  forex: { hue: 205, Icon: DollarSign, label: "FOREX" },
  us: { hue: 150, Icon: TrendingUp, label: "US MARKETS" },
  crypto: { hue: 32, Icon: Bitcoin, label: "CRYPTO" },
  commodities: { hue: 95, Icon: Fuel, label: "COMMODITIES" },
};
// Naməlum/boş kateqoriyada crash etməsin (CFG[category] undefined olmasın).
const DEFAULT_CFG: Cfg = { hue: 28, Icon: Newspaper, label: "MARKETS" };

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export const GeneratedThumb = memo(function GeneratedThumb({
  seed,
  category,
  className,
  compact = false,
}: {
  seed: string;
  category: Category | string;
  className?: string;
  compact?: boolean;
}) {
  const cfg = CFG[category as string] ?? DEFAULT_CFG;
  const s = hashStr(seed);
  const hue = cfg.hue + ((s % 22) - 11);
  const angle = 115 + (s % 60);
  const accent = `hsl(${hue} 82% 60%)`;
  const Icon = cfg.Icon;

  // Seed-dən deterministik chart nöqtələri (redaksiya market motivi).
  const N = 11;
  const pts = Array.from({ length: N }, (_, i) => {
    const v = hashStr(seed + "·" + i) % 1000;
    const y = 70 - (v / 1000) * 52 + Math.sin((i / N) * Math.PI) * 6; // 18–70 arası dalğa
    return [(i / (N - 1)) * 100, y] as const;
  });
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L100 100 L0 100 Z`;
  const gid = `g${s.toString(36)}`;

  return (
    <div
      className={`relative overflow-hidden ${className ?? ""}`}
      style={{
        background: `linear-gradient(${angle}deg, hsl(${hue} 44% 17%), hsl(${hue} 52% 10%) 62%, #0a0a0b)`,
      }}
      aria-hidden
    >
      {/* yumşaq işıq ləkəsi — kompaktda kiçilir (192px ləkə 96px qutunu tam örtərdi) */}
      <div
        className={
          compact
            ? "absolute -right-5 -top-6 h-20 w-20 rounded-full blur-2xl"
            : "absolute -right-12 -top-14 h-48 w-48 rounded-full blur-3xl"
        }
        style={{ background: accent, opacity: 0.2 }}
      />

      {/* solğun nöqtə toxuması */}
      <div
        className="absolute inset-0 opacity-[0.1]"
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,.8) 1px, transparent 1px)",
          backgroundSize: compact ? "10px 10px" : "18px 18px",
        }}
      />

      {/* solğun kateqoriya qlifi (su nişanı) */}
      <Icon
        size={compact ? 40 : 104}
        className="absolute -right-3 top-1/2 -translate-y-1/2 opacity-[0.12]"
        style={{ color: accent }}
        strokeWidth={1.5}
      />

      {/* redaksiya market motivi — seed-dən chart sahəsi */}
      <svg
        className="absolute inset-x-0 bottom-0 h-[62%] w-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity="0.32" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill={`url(#${gid})`} />
        <path d={line} fill="none" stroke={accent} strokeWidth="1.4" strokeOpacity="0.7" vectorEffect="non-scaling-stroke" />
      </svg>

      {/* kateqoriya etiketi + wordmark — yalnız iri örtükdə (kiçikdə kəsilir) */}
      {!compact && (
        <>
          <span
            className="absolute left-3.5 top-3 font-mono text-[10px] font-semibold tracking-[0.18em]"
            style={{ color: accent }}
          >
            {cfg.label}
          </span>
          <span className="absolute bottom-2.5 left-3.5 font-mono text-[10px] font-semibold tracking-wider text-white/85">
            Nexus<span style={{ color: accent }}>IQ</span>
          </span>
        </>
      )}
    </div>
  );
});
