"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { getAssetsOverview, getTotalNewsCount } from "@/lib/api";

type Col = { titleKey: string; links: { href: string; labelKey: string }[] };

const COLUMNS: Col[] = [
  {
    titleKey: "navg.market",
    links: [
      { href: "/assets", labelKey: "nav.assets" },
      { href: "/markets", labelKey: "nav.markets" },
      { href: "/watchlist", labelKey: "nav.watchlist" },
      { href: "/portfel", labelKey: "nav.portfel" },
    ],
  },
  {
    titleKey: "navg.analysis",
    links: [
      { href: "/anomalies", labelKey: "anom.nav" },
      { href: "/analogs", labelKey: "analog.nav" },
      { href: "/correlation", labelKey: "corr.nav" },
      { href: "/powerlaw", labelKey: "pl.nav" },
    ],
  },
  {
    titleKey: "foot.tools",
    links: [
      { href: "/compare", labelKey: "nav.compare" },
      { href: "/accuracy", labelKey: "nav.accuracy" },
      { href: "/radar", labelKey: "nav.radar" },
      { href: "/alerts", labelKey: "nav.alerts" },
    ],
  },
  {
    titleKey: "foot.more",
    links: [
      { href: "/", labelKey: "nav.news" },
      { href: "/saved", labelKey: "bm.title" },
      { href: "/about", labelKey: "about.nav" },
    ],
  },
];

export function Footer() {
  const { t, lang } = useI18n();
  const year = new Date().getFullYear();
  const [news, setNews] = useState<number | null>(null);
  const [assets, setAssets] = useState<number | null>(null);

  useEffect(() => {
    getTotalNewsCount().then((n) => {
      if (n > 0) setNews(Math.floor(n / 100) * 100);
    });
    getAssetsOverview().then((a) => {
      if (a.length) setAssets(a.length);
    });
  }, []);

  return (
    <footer className="mt-auto border-t border-border bg-surface">
      <div className="shell py-12">
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(4,1fr)]">
          {/* brend */}
          <div className="max-w-xs">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
              <span className="text-lg font-semibold tracking-tight">
                Nexus<span className="text-accent">IQ</span>
              </span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              {t("foot.tagline")}
            </p>
            <div className="mt-5 inline-flex items-center gap-2 rounded-lg border border-border bg-bg px-3 py-1.5">
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-up" />
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                {t("foot.live")}
              </span>
            </div>
          </div>

          {/* keçid sütunları */}
          {COLUMNS.map((col) => (
            <nav key={col.titleKey} className="flex flex-col gap-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted">
                {t(col.titleKey)}
              </p>
              {col.links.map((l) => (
                <Link
                  key={l.href + l.labelKey}
                  href={l.href}
                  className="w-fit text-sm text-text transition-colors hover:text-accent"
                >
                  {t(l.labelKey)}
                </Link>
              ))}
            </nav>
          ))}
        </div>

        {/* canlı statistika */}
        <div className="mt-10 flex flex-wrap items-center gap-x-10 gap-y-4 border-t border-border pt-6">
          {[
            {
              value: `${(news ?? 1500).toLocaleString(lang)}+`,
              label: t("foot.statsNews"),
            },
            { value: `${assets ?? 80}+`, label: t("foot.statsAssets") },
            { value: "4", label: t("foot.statsLangs") },
          ].map((s) => (
            <div key={s.label} className="flex items-baseline gap-2">
              <span className="font-mono text-lg font-semibold text-accent">
                {s.value}
              </span>
              <span className="text-xs uppercase tracking-[0.14em] text-muted">
                {s.label}
              </span>
            </div>
          ))}
        </div>

        {/* alt zolaq */}
        <div className="mt-10 flex flex-col gap-4 border-t border-border pt-6 text-xs text-muted md:flex-row md:items-center md:justify-between">
          <p className="max-w-xl leading-relaxed">
            © {year} NexusIQ. {t("foot.rights")} {t("foot.disclaimer")}
          </p>
          <p className="flex shrink-0 items-center gap-2 font-mono uppercase tracking-[0.16em]">
            <span className="text-muted">{t("foot.sysLabel")}:</span>
            <span className="inline-flex items-center gap-1.5 text-up">
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-up" />
              {t("foot.sysOn")}
            </span>
          </p>
        </div>
      </div>
    </footer>
  );
}
