"use client";

import { useMemo } from "react";
import { useI18n } from "@/lib/i18n";
import type { CorrMatrix } from "@/types";

/**
 * Fokus-aktiv korrelyasiya görünüşü — matrisdən qat-qat sadə.
 *
 * Bir aktiv seçilir; qalan hamısı onunla korrelyasiyaya görə ən müsbətdən
 * ən mənfiyə sıralanır. Hər sətir mərkəzdən divergent zolaq (sağ=yaşıl/birlikdə,
 * sol=qırmızı/əks). Sətrə klik → cüt analizi açılır.
 */
export function CorrelationFocus({
  data,
  focus,
  selected,
  onFocus,
  onSelect,
}: {
  data: CorrMatrix;
  focus: string;
  selected?: { a: string; b: string };
  onFocus: (key: string) => void;
  onSelect: (a: string, b: string) => void;
}) {
  const { t } = useI18n();
  const { assets, matrix } = data;

  const focusIdx = assets.findIndex((a) => a.key === focus);
  const focusLabel = assets[focusIdx]?.label ?? focus;

  const rows = useMemo(() => {
    if (focusIdx < 0) return [];
    const r = matrix[focusIdx] ?? [];
    return assets
      .map((a, j) => ({ key: a.key, label: a.label, value: r[j] }))
      .filter((x) => x.key !== focus && x.value !== null && x.value !== undefined)
      .sort((a, b) => (b.value as number) - (a.value as number)) as {
      key: string;
      label: string;
      value: number;
    }[];
  }, [assets, matrix, focusIdx, focus]);

  return (
    <div>
      {/* fokus seçici */}
      <div className="mb-5">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted">
          {t("corr.focus")}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {assets.map((a) => (
            <button
              key={a.key}
              onClick={() => onFocus(a.key)}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                a.key === focus
                  ? "bg-accent text-black"
                  : "border border-border bg-surface text-muted hover:text-text"
              }`}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>

      {/* sıralama */}
      <div className="space-y-0.5">
        {rows.map((row) => {
          const v = row.value;
          const pos = v >= 0;
          const mag = Math.min(1, Math.abs(v)) * 50; // mərkəzdən % en
          const color = pos ? "var(--up)" : "var(--down)";
          const isSel =
            selected &&
            ((selected.a === focus && selected.b === row.key) ||
              (selected.a === row.key && selected.b === focus));
          return (
            <button
              key={row.key}
              onClick={() => onSelect(focus, row.key)}
              className={`group flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors ${
                isSel ? "bg-surface-hover ring-1 ring-accent" : "hover:bg-surface-hover"
              }`}
            >
              <span className="w-24 shrink-0 truncate text-right text-xs font-medium">
                {row.label}
              </span>

              {/* divergent zolaq */}
              <div className="relative h-6 flex-1">
                {/* mərkəz oxu */}
                <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-border" />
                {/* zolaq */}
                <div
                  className="absolute top-1/2 h-3 -translate-y-1/2 rounded-sm transition-all group-hover:opacity-90"
                  style={{
                    left: pos ? "50%" : `${50 - mag}%`,
                    width: `${mag}%`,
                    background: color,
                    opacity: 0.4 + Math.min(1, Math.abs(v)) * 0.5,
                  }}
                />
              </div>

              <span
                className="w-12 shrink-0 text-right font-mono text-xs font-semibold"
                style={{ color }}
              >
                {v >= 0 ? "+" : ""}
                {v.toFixed(2)}
              </span>
            </button>
          );
        })}
      </div>

      <p className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted">
        <span className="flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ background: "var(--up)" }}
          />
          {focusLabel} {t("corr.withFocus")} → {t("corr.positive")}
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ background: "var(--down)" }}
          />
          {t("corr.negative")}
        </span>
      </p>
    </div>
  );
}
