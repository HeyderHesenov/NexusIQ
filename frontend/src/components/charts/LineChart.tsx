"use client";

export interface LineSeries {
  label: string;
  color: string;
  points: { date: string; value: number }[];
}

export const SERIES_COLORS = [
  "#ff7a1a",
  "#3b82f6",
  "#22c55e",
  "#a855f7",
  "#ef4444",
];

/**
 * Universal SVG xətt qrafiki (bir və ya bir neçə seriya).
 * normalize=true → hər seriya başlanğıcdan 100-ə nisbətdə (müqayisə üçün).
 *
 * viewBox geniş landşaft nisbətindədir və `w-full` ilə konteyneri tam tutur,
 * hündürlük en-ə görə avtomatik (təhrif yox). `height` mobil minimum üçündür.
 */
export function LineChart({
  series,
  height = 380,
  normalize = false,
}: {
  series: LineSeries[];
  height?: number;
  normalize?: boolean;
}) {
  const W = 1000;
  const H = 380;
  const PAD = { top: 22, right: 64, bottom: 34, left: 56 };

  const norm = series
    .filter((s) => s.points.length >= 2)
    .map((s) => {
      const base = s.points[0].value || 1;
      return {
        ...s,
        vals: s.points.map((p) =>
          normalize ? (p.value / base) * 100 : p.value,
        ),
      };
    });

  if (norm.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted"
        style={{ height }}
      >
        Müqayisə üçün ən azı bir aktiv seç.
      </div>
    );
  }

  const len = Math.max(...norm.map((s) => s.vals.length));
  const allY = norm.flatMap((s) => s.vals);
  const minY = Math.min(...allY);
  const maxY = Math.max(...allY);
  const spanY = maxY - minY || 1;

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const sx = (i: number) => PAD.left + (i / (len - 1)) * innerW;
  const sy = (v: number) => PAD.top + innerH - ((v - minY) / spanY) * innerH;

  const ticks = Array.from({ length: 5 }, (_, i) => minY + (spanY * i) / 4);
  // Y etiketi: normallaşmada tam ədəd; qiymətdə kompakt (k/M) — kəsilməsin.
  const fmtTick = (v: number): string => {
    if (normalize) return v.toFixed(0);
    const a = Math.abs(v);
    if (a >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
    if (a >= 1_000) return `${(v / 1_000).toFixed(1)}k`;
    return v.toFixed(a < 10 ? 2 : 0);
  };
  const dates = norm[0].points.map((p) => p.date);
  const first = dates[0];
  const last = dates[dates.length - 1];

  // Lider seriya (ən yüksək son dəyər) — altına yumşaq area çəkilir.
  const lead = norm.reduce((best, s) =>
    s.vals[s.vals.length - 1] > best.vals[best.vals.length - 1] ? s : best,
  );
  const leadPath = lead.vals
    .map((v, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`)
    .join(" ");
  const leadArea = `${leadPath} L${sx(len - 1).toFixed(1)},${(H - PAD.bottom).toFixed(1)} L${PAD.left.toFixed(1)},${(H - PAD.bottom).toFixed(1)} Z`;

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ minHeight: Math.min(height, 240) }}
        role="img"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="lc-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lead.color} stopOpacity={0.16} />
            <stop offset="100%" stopColor={lead.color} stopOpacity={0} />
          </linearGradient>
        </defs>

        {/* üfüqi şəbəkə + y etiketləri */}
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
              strokeDasharray={i === 0 ? "0" : "3 5"}
            />
            <text
              x={PAD.left - 10}
              y={sy(tv) + 4}
              textAnchor="end"
              className="fill-muted font-mono text-[11px]"
            >
              {fmtTick(tv)}
            </text>
          </g>
        ))}

        {/* normallaşma bazası = 100 xətti */}
        {normalize && minY <= 100 && maxY >= 100 && (
          <line
            x1={PAD.left}
            x2={W - PAD.right}
            y1={sy(100)}
            y2={sy(100)}
            stroke="currentColor"
            className="text-muted"
            strokeWidth={1}
            strokeDasharray="2 4"
            opacity={0.5}
          />
        )}

        {/* tarix oxu */}
        <text x={PAD.left} y={H - 12} className="fill-muted font-mono text-[11px]">
          {first}
        </text>
        <text
          x={W - PAD.right}
          y={H - 12}
          textAnchor="end"
          className="fill-muted font-mono text-[11px]"
        >
          {last}
        </text>

        {/* lider seriyanın altında area */}
        <path d={leadArea} fill="url(#lc-area)" stroke="none" />

        {/* xətlər + son nöqtə dəyər çipi */}
        {norm.map((s, si) => {
          const lastV = s.vals[s.vals.length - 1];
          const cx = sx(len - 1);
          const cy = sy(lastV);
          return (
            <g key={si}>
              <path
                d={s.vals
                  .map((v, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`)
                  .join(" ")}
                fill="none"
                stroke={s.color}
                strokeWidth={2.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              <circle cx={cx} cy={cy} r={3.5} fill={s.color} />
              <text
                x={cx + 8}
                y={cy + 4}
                className="font-mono text-[11px] font-semibold"
                fill={s.color}
              >
                {fmtTick(lastV)}
              </text>
            </g>
          );
        })}
      </svg>

      {series.length > 1 && (
        <div className="mt-3 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs">
          {norm.map((s, i) => {
            const chg = s.vals[s.vals.length - 1] - s.vals[0];
            const pct = (chg / (s.vals[0] || 1)) * 100;
            return (
              <span key={i} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-3.5 rounded-sm"
                  style={{ background: s.color }}
                />
                <span className="font-medium text-text">{s.label}</span>
                <span
                  className={`font-mono ${pct >= 0 ? "text-up" : "text-down"}`}
                >
                  {pct >= 0 ? "+" : ""}
                  {pct.toFixed(1)}%
                </span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
