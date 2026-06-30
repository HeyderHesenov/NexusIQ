"use client";

import {
  Activity,
  Bell,
  CandlestickChart,
  Check,
  Newspaper,
  Sparkles,
} from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { useI18n } from "@/lib/i18n";

export default function AboutPage() {
  const { t } = useI18n();

  const features = [
    { icon: Newspaper, title: t("about.fNewsT"), desc: t("about.fNewsD") },
    { icon: CandlestickChart, title: t("about.fMarketT"), desc: t("about.fMarketD") },
    { icon: Activity, title: t("about.fAnalyticsT"), desc: t("about.fAnalyticsD") },
    { icon: Bell, title: t("about.fAlertsT"), desc: t("about.fAlertsD") },
  ];

  const aiCaps = [
    t("about.aiCap1"),
    t("about.aiCap2"),
    t("about.aiCap3"),
    t("about.aiCap4"),
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-4xl px-5 py-12 flex-1">
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

        {/* məqsəd */}
        <section className="py-10">
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
