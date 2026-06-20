"use client";

import { Bitcoin, DollarSign, LineChart, Fuel } from "lucide-react";
import type { Category } from "@/types";

/**
 * Brendli generativ thumbnail — hər xəbər üçün kodla yaradılan unikal şəkil.
 * Heç bir xarici şəkil yoxdur (müəllif hüququ təmiz). Forma xəbərin id-sindən
 * deterministik çıxır: eyni xəbər → eyni şəkil, fərqli xəbər → fərqli motiv.
 */
const CFG: Record<Category, { hue: number; Icon: typeof Bitcoin }> = {
  forex: { hue: 205, Icon: DollarSign },
  us: { hue: 150, Icon: LineChart },
  crypto: { hue: 32, Icon: Bitcoin },
  commodities: { hue: 95, Icon: Fuel },
};

const W = 400;
const H = 225;

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Toxumdan deterministik qiymət xətti. */
function chartPath(seed: number): { line: string; area: string } {
  const M = 26;
  const f1 = 1 + (seed % 3);
  const f2 = 2 + ((seed >> 2) % 3);
  const p1 = (seed % 7) * 0.5;
  const p2 = ((seed >> 3) % 6) * 0.5;
  const amp = 0.16 + ((seed >> 5) % 5) * 0.012;
  let line = "";
  for (let i = 0; i <= M; i++) {
    const x = (i / M) * W;
    const t = (i / M) * Math.PI * 2;
    const y =
      H * 0.56 -
      Math.sin(t * f1 + p1) * H * amp -
      Math.sin(t * f2 + p2) * H * 0.08;
    line += (i === 0 ? "M" : "L") + x.toFixed(1) + "," + y.toFixed(1) + " ";
  }
  return { line, area: `${line} L${W},${H} L0,${H} Z` };
}

export function GeneratedThumb({
  seed,
  category,
  className,
}: {
  seed: string;
  category: Category;
  className?: string;
}) {
  const cfg = CFG[category];
  const s = hashStr(seed);
  const hue = cfg.hue + ((s % 22) - 11);
  const color = `hsl(${hue} 85% 60%)`;
  const { line, area } = chartPath(s);
  const gid = `gt-${category}-${s}`;
  const Icon = cfg.Icon;

  return (
    <div
      className={`relative overflow-hidden ${className ?? ""}`}
      style={{
        background: `linear-gradient(135deg, hsl(${hue} 45% 11%), #0a0a0b 72%)`,
      }}
      aria-hidden
    >
      {/* grid fonu */}
      <div
        className="absolute inset-0 opacity-[0.10]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.6) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.6) 1px,transparent 1px)",
          backgroundSize: "26px 26px",
        }}
      />

      {/* solğun kateqoriya ikonu */}
      <Icon
        size={118}
        className="absolute -right-4 -top-4 opacity-[0.10]"
        style={{ color }}
        strokeWidth={1.5}
      />

      {/* qiymət xətti */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="absolute inset-0 h-full w-full"
      >
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.30" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill={`url(#${gid})`} />
        <path
          d={line}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          style={{ filter: `drop-shadow(0 0 5px ${color}55)` }}
        />
      </svg>

      {/* wordmark */}
      <span
        className="absolute bottom-2.5 left-3.5 font-mono text-[10px] font-semibold tracking-wider"
        style={{ color }}
      >
        Nexus<span className="text-white/70">IQ</span>
      </span>
    </div>
  );
}
