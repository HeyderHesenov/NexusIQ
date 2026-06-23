"use client";

import { useI18n } from "@/lib/i18n";

/** Bal səviyyəsinə görə rəng — yüksək=accent, orta=amber, aşağı=muted. */
export function tierColor(score: number): string {
  if (score >= 65) return "var(--accent)";
  if (score >= 45) return "#fbbf24";
  return "var(--muted)";
}

/** Tema açarını oxunaqlı teqə çevir (ai_data → AI Data). */
export function themeLabel(theme: string): string {
  return theme
    .split("_")
    .map((w) => (w.length <= 3 ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1)))
    .join(" ");
}

/** Signature — fürsət balı radial halqası (0..100). */
export function ScoreRing({ score, size = 68 }: { score: number; size?: number }) {
  const stroke = size >= 96 ? 6 : 5;
  const r = size / 2 - stroke - 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(100, score)) / 100);
  const color = tierColor(score);
  return (
    <div className="relative shrink-0" style={{ height: size, width: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span
          className="font-mono font-semibold tabular-nums"
          style={{ color, fontSize: size >= 96 ? 26 : 18 }}
        >
          {Math.round(score)}
        </span>
      </div>
    </div>
  );
}

/** Bal komponentləri — hər biri stacked: etiket+dəyər üstdə, bar tam enli altda. */
export function ScoreBars({ breakdown }: { breakdown: Record<string, number> }) {
  const { t } = useI18n();
  return (
    <div className="grid grid-cols-3 gap-x-3 gap-y-2 sm:gap-x-4">
      {Object.entries(breakdown).map(([key, v]) => {
        const color = tierColor(v);
        return (
          <div key={key}>
            <div className="flex items-baseline justify-between gap-1.5">
              <span className="truncate text-[10px] font-medium uppercase tracking-wide text-muted">
                {t(`radar.bd.${key}`)}
              </span>
              <span
                className="font-mono text-[11px] font-semibold tabular-nums"
                style={{ color }}
              >
                {Math.round(v)}
              </span>
            </div>
            <span className="mt-1.5 block h-1 overflow-hidden rounded-full bg-border">
              <span
                className="block h-full rounded-full motion-safe:transition-[width] motion-safe:duration-500"
                style={{ width: `${v}%`, background: color }}
              />
            </span>
          </div>
        );
      })}
    </div>
  );
}
