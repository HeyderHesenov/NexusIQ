"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkline } from "@/components/charts/Sparkline";
import { NewsBadges } from "@/components/news/NewsBadges";
import { getWatchlistIntel } from "@/lib/api";
import { getLastSeen, markSeen } from "@/lib/lastSeen";
import { useWatchlist } from "@/lib/watchlist";
import { localizedNews } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { AssetDigest } from "@/types";

/**
 * "Mənə Aid" — şəxsi hero digest. Yalnız SƏNİN izlədiyin aktivlərə toxunan
 * xəbərlər, aktiv üzrə qruplanmış. İmza: "sən yox ikən" təzəlik nəbzi (pulse-dot).
 * Watchlist boşdursa və ya heç xəbər yoxdursa görünmür (utanc verici boşluq yox).
 */
export function RelevantToMe() {
  const { t, lang } = useI18n();
  const keys = useWatchlist();
  const keyStr = keys.join(",");
  const [assets, setAssets] = useState<AssetDigest[] | null>(null);
  const [since, setSince] = useState(0);

  useEffect(() => {
    if (keys.length === 0) {
      setAssets([]);
      return;
    }
    let alive = true;
    getWatchlistIntel(keys, getLastSeen()).then((d) => {
      if (!alive) return;
      setAssets(d.assets || []);
      setSince(d.sinceCount || 0);
      // Köhnə lastSeen ilə çəkdik → indi möhürlə (növbəti açılışda "yeni" dəqiqdir).
      markSeen();
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyStr]);

  if (!assets || assets.length === 0) return null;

  return (
    <section className="fade-up mb-8">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
            {t("meneAid.eyebrow")}
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">
            {since > 0 ? (
              <>
                {t("meneAid.awayPre")}{" "}
                <span className="text-accent">{since}</span>{" "}
                {t("meneAid.awayPost")}
              </>
            ) : (
              t("meneAid.heading")
            )}
          </h2>
        </div>
      </div>

      <div className="no-scrollbar flex gap-3 overflow-x-auto pb-2">
        {assets.map((a) => (
          <AssetPulseCard key={a.key} a={a} lang={lang} t={t} />
        ))}
      </div>
    </section>
  );
}

function AssetPulseCard({
  a,
  lang,
  t,
}: {
  a: AssetDigest;
  lang: string;
  t: (k: string) => string;
}) {
  const top = a.news[0];
  const title = top ? localizedNews(top, lang).title : "";
  const fresh = a.sinceCount > 0;

  return (
    <Link
      href={`/mene-aid/${a.key}`}
      className="group flex w-72 shrink-0 flex-col gap-2.5 rounded-card border border-border bg-surface p-3.5 transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/50"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm font-semibold tracking-tight text-text">
          {a.label}
        </span>
        {fresh ? (
          <span className="flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent-soft px-2 py-0.5 font-mono text-[10px] font-semibold text-accent">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-accent" />
            +{a.sinceCount} {t("meneAid.new")}
          </span>
        ) : (
          <span className="font-mono text-[10px] text-muted">
            {a.count} {t("meneAid.items")}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Sparkline values={a.sentimentTrend} width={72} height={22} />
        {top && <NewsBadges sentiment={top.sentiment} impact={top.impactScore} />}
      </div>

      <p className="line-clamp-2 min-h-[2.5rem] text-sm font-medium leading-snug text-text">
        {title || t("meneAid.quiet")}
      </p>

      <span className="mt-auto flex items-center justify-between text-[11px] text-muted">
        <span className="truncate">{top?.source ?? "—"}</span>
        <span className="shrink-0 text-accent opacity-0 transition-opacity group-hover:opacity-100">
          {t("meneAid.open")} →
        </span>
      </span>
    </Link>
  );
}
