"use client";

/** Kiçik trend qrafiki (CMC/Binance tərzi) — oxsuz, trendə görə rəngli. */
export function Sparkline({
  values,
  width = 112,
  height = 36,
}: {
  values: number[];
  width?: number;
  height?: number;
}) {
  if (!values || values.length < 2) {
    return <div style={{ width, height }} />;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 3;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;

  const x = (i: number) => pad + (i / (values.length - 1)) * innerW;
  const y = (v: number) => pad + innerH - ((v - min) / span) * innerH;

  const line = values
    .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
    .join(" ");
  const area = `${line} L${x(values.length - 1).toFixed(1)},${height} L${x(0).toFixed(1)},${height} Z`;

  const up = values[values.length - 1] >= values[0];
  const cls = up ? "text-up" : "text-down";
  const gid = `sp-${up ? "u" : "d"}-${Math.round(values[0])}-${values.length}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cls}
      aria-hidden
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.22" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path
        d={line}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
