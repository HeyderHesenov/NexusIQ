"use client";

import type { CorrPairPoint } from "@/types";

/** İki normallaşmış qiymət seriyasını (başlanğıc=100) SVG xətt qrafiki kimi çəkir. */
export function PairChart({
  series,
  labelA,
  labelB,
}: {
  series: CorrPairPoint[];
  labelA: string;
  labelB: string;
}) {
  const W = 760;
  const H = 280;
  const PAD = { top: 16, right: 16, bottom: 28, left: 44 };

  if (series.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted">
        —
      </div>
    );
  }

  const xs = series.map((_, i) => i);
  const allY = series.flatMap((p) => [p.a, p.b]);
  const minY = Math.min(...allY);
  const maxY = Math.max(...allY);
  const spanY = maxY - minY || 1;

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const sx = (i: number) => PAD.left + (i / (xs.length - 1)) * innerW;
  const sy = (v: number) => PAD.top + innerH - ((v - minY) / spanY) * innerH;

  const path = (key: "a" | "b") =>
    series
      .map((p, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(p[key]).toFixed(1)}`)
      .join(" ");

  // y oxu üçün 4 nişan.
  const ticks = Array.from({ length: 4 }, (_, i) => minY + (spanY * i) / 3);
  const first = series[0].date;
  const last = series[series.length - 1].date;

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[600px]" role="img">
        {/* y grid + etiketlər */}
        {ticks.map((tv, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={sy(tv)}
              y2={sy(tv)}
              stroke="currentColor"
              className="text-border"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 6}
              y={sy(tv) + 3}
              textAnchor="end"
              className="fill-muted font-mono text-[9px]"
            >
              {tv.toFixed(0)}
            </text>
          </g>
        ))}

        {/* x etiketləri */}
        <text x={PAD.left} y={H - 8} className="fill-muted font-mono text-[9px]">
          {first}
        </text>
        <text
          x={W - PAD.right}
          y={H - 8}
          textAnchor="end"
          className="fill-muted font-mono text-[9px]"
        >
          {last}
        </text>

        {/* xətlər */}
        <path d={path("a")} fill="none" stroke="#ff7a1a" strokeWidth={2} />
        <path d={path("b")} fill="none" stroke="#3b82f6" strokeWidth={2} />
      </svg>

      {/* legend */}
      <div className="mt-2 flex items-center justify-center gap-5 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm" style={{ background: "#ff7a1a" }} />
          {labelA}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm" style={{ background: "#3b82f6" }} />
          {labelB}
        </span>
      </div>
    </div>
  );
}
