"use client";

import type { CorrMatrix } from "@/types";

/** Korrelyasiya dəyərini rəngə çevirir: müsbət=yaşıl, mənfi=qırmızı, sıfır=sönük. */
function cellColor(v: number | null): string {
  if (v === null) return "transparent";
  const a = Math.min(1, Math.abs(v)) * 0.85;
  if (v >= 0) return `rgba(34, 197, 94, ${a})`;
  return `rgba(239, 68, 68, ${a})`;
}

function textColor(v: number | null): string {
  if (v === null) return "text-muted";
  return Math.abs(v) > 0.45 ? "text-white" : "text-text";
}

/** Pearson korrelyasiya heatmap-ı. Xanaya klik → cüt seçilir. */
export function CorrelationMatrix({
  data,
  selected,
  onSelect,
}: {
  data: CorrMatrix;
  selected?: { a: string; b: string };
  onSelect: (a: string, b: string) => void;
}) {
  const { assets, matrix } = data;
  if (!matrix.length) {
    return (
      <div className="rounded-card border border-dashed border-border py-16 text-center text-sm text-muted">
        —
      </div>
    );
  }

  return (
    <div className="no-scrollbar overflow-x-auto">
      <table className="border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-bg" />
            {assets.map((a) => (
              <th
                key={a.key}
                className="px-1 pb-1 text-center font-mono text-[10px] font-medium text-muted"
              >
                {a.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {assets.map((row, i) => (
            <tr key={row.key}>
              <th className="sticky left-0 z-10 bg-bg pr-2 text-right font-mono text-[10px] font-medium text-muted">
                {row.label}
              </th>
              {assets.map((col, j) => {
                const v = matrix[i]?.[j] ?? null;
                const isDiag = i === j;
                const isSel =
                  selected &&
                  ((selected.a === row.key && selected.b === col.key) ||
                    (selected.a === col.key && selected.b === row.key));
                return (
                  <td key={col.key} className="p-0">
                    <button
                      disabled={isDiag || v === null}
                      onClick={() => onSelect(row.key, col.key)}
                      title={`${row.label} · ${col.label}: ${v ?? "—"}`}
                      style={{ backgroundColor: isDiag ? "transparent" : cellColor(v) }}
                      className={`h-10 w-12 rounded-md text-center font-mono text-[11px] transition-all ${textColor(
                        v,
                      )} ${
                        isDiag
                          ? "cursor-default border border-border bg-surface text-muted"
                          : "hover:ring-2 hover:ring-accent"
                      } ${isSel ? "ring-2 ring-accent" : ""}`}
                    >
                      {isDiag ? "1" : v === null ? "·" : v.toFixed(2)}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
