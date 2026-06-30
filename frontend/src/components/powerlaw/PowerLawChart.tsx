"use client";

import type { PowerLawPoint } from "@/types";
import { useI18n } from "@/lib/i18n";

/** BTC power-law dəhlizi — LOG şkalada faktiki qiymət + model + dəstək/müqavimət. */
export function PowerLawChart({ series }: { series: PowerLawPoint[] }) {
  const { t } = useI18n();
  const W = 820;
  const H = 360;
  const PAD = { top: 16, right: 16, bottom: 28, left: 56 };

  if (series.length < 2) {
    return <div className="flex h-64 items-center justify-center text-muted">—</div>;
  }

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const lg = (v: number) => Math.log10(Math.max(v, 0.0001));
  const lows = series.map((p) => lg(p.low));
  const highs = series.map((p) => lg(p.high));
  const minY = Math.min(...lows);
  const maxY = Math.max(...highs);
  const spanY = maxY - minY || 1;

  const sx = (i: number) => PAD.left + (i / (series.length - 1)) * innerW;
  const sy = (v: number) => PAD.top + innerH - ((lg(v) - minY) / spanY) * innerH;

  const path = (sel: (p: PowerLawPoint) => number) =>
    series
      .map((p, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(sel(p)).toFixed(1)}`)
      .join(" ");

  const corridor =
    path((p) => p.high) +
    " " +
    series
      .map((_, i) => `L${sx(series.length - 1 - i).toFixed(1)},${sy(series[series.length - 1 - i].low).toFixed(1)}`)
      .join(" ") +
    " Z";

  // log10 tam dərəcələrində Y nişanları (1k, 10k, 100k...)
  const ticks: number[] = [];
  for (let e = Math.ceil(minY); e <= Math.floor(maxY); e++) ticks.push(e);

  const fmt = (exp: number) => {
    const v = 10 ** exp;
    if (v >= 1000) return `$${(v / 1000).toLocaleString()}k`;
    return `$${v}`;
  };

  const lastI = series.length - 1;

  return (
    <div className="no-scrollbar w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[640px]" role="img">
        {/* dəstək–müqavimət dəhlizi */}
        <path d={corridor} fill="#ff7a1a" opacity={0.08} />

        {/* Y grid + log nişanları */}
        {ticks.map((e) => (
          <g key={e}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={sy(10 ** e)}
              y2={sy(10 ** e)}
              stroke="currentColor"
              className="text-border"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 6}
              y={sy(10 ** e) + 3}
              textAnchor="end"
              className="fill-muted font-mono text-[9px]"
            >
              {fmt(e)}
            </text>
          </g>
        ))}

        {/* dəstək / müqavimət xətləri */}
        <path d={path((p) => p.low)} fill="none" stroke="#ff7a1a" strokeWidth={1} strokeDasharray="3 3" opacity={0.5} />
        <path d={path((p) => p.high)} fill="none" stroke="#ff7a1a" strokeWidth={1} strokeDasharray="3 3" opacity={0.5} />

        {/* model (ədalətli dəyər) */}
        <path d={path((p) => p.model)} fill="none" stroke="#ff7a1a" strokeWidth={2} />

        {/* faktiki qiymət */}
        <path
          d={path((p) => p.actual)}
          fill="none"
          stroke="currentColor"
          className="text-text"
          strokeWidth={2}
        />

        {/* "indi" markeri */}
        <circle cx={sx(lastI)} cy={sy(series[lastI].actual)} r={4} className="fill-text" />

        {/* x etiketləri */}
        <text x={PAD.left} y={H - 8} className="fill-muted font-mono text-[9px]">
          {series[0].date}
        </text>
        <text x={W - PAD.right} y={H - 8} textAnchor="end" className="fill-muted font-mono text-[9px]">
          {series[lastI].date}
        </text>
      </svg>

      <div className="mt-2 flex flex-wrap items-center justify-center gap-4 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm bg-text" /> {t("pl.actual")}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm" style={{ background: "#ff7a1a" }} /> {t("pl.fair")}
        </span>
      </div>
    </div>
  );
}
