"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Bell,
  CandlestickChart,
  Check,
  GitCompareArrows,
  Newspaper,
  Radar,
  ScrollText,
  Sparkles,
  Target,
  UserRoundCheck,
  Wallet,
} from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { getAssetsOverview, getTotalNewsCount } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function AboutPage() {
  const { t, lang } = useI18n();
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

  const features = [
    { icon: Newspaper, title: t("about.fNewsT"), desc: t("about.fNewsD") },
    { icon: CandlestickChart, title: t("about.fMarketT"), desc: t("about.fMarketD") },
    { icon: Activity, title: t("about.fAnalyticsT"), desc: t("about.fAnalyticsD") },
    { icon: Bell, title: t("about.fAlertsT"), desc: t("about.fAlertsD") },
    { icon: Wallet, title: t("about.fPortfolioT"), desc: t("about.fPortfolioD") },
    { icon: Target, title: t("about.fAccuracyT"), desc: t("about.fAccuracyD") },
    { icon: GitCompareArrows, title: t("about.fCompareT"), desc: t("about.fCompareD") },
    { icon: Radar, title: t("about.fRadarT"), desc: t("about.fRadarD") },
    { icon: ScrollText, title: t("about.fBriefT"), desc: t("about.fBriefD") },
    { icon: UserRoundCheck, title: t("about.fMeneAidT"), desc: t("about.fMeneAidD") },
  ];

  const aiCaps = [
    t("about.aiCap1"),
    t("about.aiCap2"),
    t("about.aiCap3"),
    t("about.aiCap4"),
  ];

  const stats = [
    { value: `${assets ?? 80}+`, label: t("about.statAssets") },
    { value: "4", label: t("about.statLangs") },
    {
      value: `${(news ?? 1500).toLocaleString(lang)}+`,
      label: t("about.statNews"),
    },
    { value: `${features.length}`, label: t("about.statFeatures") },
  ];

  const steps = [1, 2, 3, 4, 5].map((n) => ({
    title: t(`about.step${n}T`),
    desc: t(`about.step${n}D`),
  }));

  const faqs = [1, 2, 3, 4, 5].map((n) => ({
    q: t(`about.faqQ${n}`),
    a: t(`about.faqA${n}`),
  }));

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell-narrow py-12 flex-1">
        {/* hero — tezis */}
        <header className="border-b border-border pb-10">
          <p className="mb-4 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-accent" />
            {t("about.eyebrow")}
          </p>
          <h1 className="max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
            {t("about.heroLead")}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted">
            {t("about.heroSub")}
          </p>
        </header>

        {/* statistika zolağı */}
        <section className="grid grid-cols-2 gap-4 py-10 sm:grid-cols-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-card border border-border bg-surface p-5"
            >
              <div className="text-3xl font-semibold text-accent">{s.value}</div>
              <div className="mt-1 text-xs uppercase tracking-[0.14em] text-muted">
                {s.label}
              </div>
            </div>
          ))}
        </section>

        {/* məqsəd */}
        <section className="border-t border-border py-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-accent">
            {t("about.purposeTitle")}
          </h2>
          <p className="max-w-3xl text-[15px] leading-relaxed text-text">
            {t("about.purpose")}
          </p>
        </section>

        {/* özəlliklər indeksi */}
        <section className="border-t border-border py-10">
          <h2 className="mb-6 text-xl font-semibold tracking-tight">
            {t("about.featTitle")}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {features.map((f) => (
              <div
                key={f.title}
                className="rounded-card border border-border bg-surface p-5"
              >
                <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <f.icon size={18} />
                </div>
                <h3 className="mb-1.5 text-sm font-semibold">{f.title}</h3>
                <p className="text-sm leading-relaxed text-muted">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* necə işləyir */}
        <section className="border-t border-border py-10">
          <h2 className="mb-6 text-xl font-semibold tracking-tight">
            {t("about.howTitle")}
          </h2>
          <ol className="flex flex-col gap-3">
            {steps.map((s, i) => (
              <li
                key={s.title}
                className="flex items-start gap-4 rounded-card border border-border bg-surface p-5"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft font-mono text-sm font-semibold text-accent">
                  {i + 1}
                </span>
                <div>
                  <h3 className="mb-1 text-sm font-semibold">{s.title}</h3>
                  <p className="text-sm leading-relaxed text-muted">{s.desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* AI Assistant — signature bölmə */}
        <section className="border-t border-border py-10">
          <div className="rounded-card border border-accent/30 bg-accent-soft p-6 sm:p-7">
            <div className="mb-3 flex items-center gap-2.5">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-black">
                <Sparkles size={18} />
              </span>
              <h2 className="text-lg font-semibold tracking-tight">
                {t("about.aiTitle")}
              </h2>
            </div>
            <p className="max-w-2xl text-[15px] leading-relaxed text-text">
              {t("about.aiLead")}
            </p>
            <ul className="mt-5 grid gap-2.5 sm:grid-cols-2">
              {aiCaps.map((cap) => (
                <li key={cap} className="flex items-start gap-2.5 text-sm text-text">
                  <Check
                    size={16}
                    className="mt-0.5 shrink-0 text-accent"
                    aria-hidden
                  />
                  <span className="leading-snug">{cap}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* tez-tez verilən suallar */}
        <section className="border-t border-border py-10">
          <h2 className="mb-6 text-xl font-semibold tracking-tight">
            {t("about.faqTitle")}
          </h2>
          <dl className="divide-y divide-border">
            {faqs.map((f) => (
              <div key={f.q} className="py-4 first:pt-0 last:pb-0">
                <dt className="text-sm font-semibold text-text">{f.q}</dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-muted">
                  {f.a}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        {/* məxfilik / data */}
        <section className="border-t border-border py-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-accent">
            {t("about.privacyTitle")}
          </h2>
          <p className="max-w-3xl text-sm leading-relaxed text-muted">
            {t("about.privacy")}
          </p>
        </section>

        {/* dürüst qeyd + etiketlər */}
        <section className="border-t border-border pt-8">
          <p className="max-w-3xl text-sm leading-relaxed text-muted">
            {t("about.disclaimer")}
          </p>
          <p className="mt-4 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
            {t("about.tags")}
          </p>
        </section>
      </main>
      <Footer />
    </div>
  );
}
