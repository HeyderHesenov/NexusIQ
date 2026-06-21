"use client";

import { useI18n } from "@/lib/i18n";

/** Sentiment + Market Impact rozetləri (xəbər kartı və detal səhifəsi üçün). */
export function NewsBadges({
  sentiment,
  impact,
}: {
  sentiment?: number | null;
  impact?: number | null;
}) {
  const { t } = useI18n();
  const hasS = sentiment !== null && sentiment !== undefined;
  const hasI = impact !== null && impact !== undefined && impact > 0;
  if (!hasS && !hasI) return null;

  const sLabel =
    !hasS || Math.abs(sentiment!) < 0.1
      ? t("news.sentNeutral")
      : sentiment! > 0
        ? t("news.sentPos")
        : t("news.sentNeg");
  const sColor =
    !hasS || Math.abs(sentiment!) < 0.1
      ? "text-muted border-border"
      : sentiment! > 0
        ? "text-up border-up/40"
        : "text-down border-down/40";

  const impactColor =
    (impact ?? 0) >= 66
      ? "text-down border-down/40"
      : (impact ?? 0) >= 33
        ? "text-accent border-accent/40"
        : "text-muted border-border";

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {hasS && (
        <span
          className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] ${sColor}`}
        >
          {sLabel}
        </span>
      )}
      {hasI && (
        <span
          className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] ${impactColor}`}
          title={t("news.impact")}
        >
          {t("news.impact")} {Math.round(impact!)}
        </span>
      )}
    </div>
  );
}
