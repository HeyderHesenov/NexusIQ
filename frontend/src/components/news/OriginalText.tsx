"use client";

import { useEffect, useState } from "react";
import { getTranslatedContent } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/**
 * "Orijinal Xəbər" — tam mətn, seçilmiş dilə tərcümə olunmuş (lazy yüklənir).
 * `fallback` tərcümə hazır olana qədər / alınmasa göstərilir.
 */
export function OriginalText({ id, fallback }: { id: string; fallback: string }) {
  const { t, lang } = useI18n();
  const [text, setText] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setText(null);
    getTranslatedContent(id, lang).then((d) => {
      if (alive) setText(d.text || fallback);
    });
    return () => {
      alive = false;
    };
  }, [id, lang, fallback]);

  return (
    <section className="mt-8">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
          {t("news.originalText")}
        </h2>
        <span className="text-[11px] text-muted/70">{t("news.originalNote")}</span>
      </div>

      {text === null ? (
        <div className="space-y-2.5">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-4 animate-pulse rounded bg-surface-hover"
              style={{ width: `${[100, 96, 98, 70][i]}%` }}
            />
          ))}
        </div>
      ) : (
        <p className="whitespace-pre-line text-[15px] leading-relaxed text-text/80">
          {text}
        </p>
      )}
    </section>
  );
}
