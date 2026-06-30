"use client";

import { useEffect, useState } from "react";
import { CalendarClock, History, Percent, Search, TrendingUp } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { AnalogPanel } from "@/components/news/HistoricalAnalogs";
import { NewsBadges } from "@/components/news/NewsBadges";
import { getNewsAnalogs, getTopImpact, searchAnalogs } from "@/lib/api";
import { localizedNews } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { AnalogResult, NewsItem } from "@/types";

// Nümunə ssenarilər — sorğu ingiliscə (embedding bazası), etiket lokallaşır.
const EXAMPLES = [
  { key: "analog.ex1", q: "Fed raises interest rates" },
  { key: "analog.ex2", q: "High CPI inflation report" },
  { key: "analog.ex3", q: "Bitcoin ETF inflows" },
  { key: "analog.ex4", q: "OPEC oil supply cut" },
] as const;

// Nəticəni necə oxumalı — istifadəçiyə yönəlik leqenda (mexanika yox).
const LEGEND = [
  { icon: TrendingUp, cls: "text-up", t: "analog.read1t", d: "analog.read1d" },
  { icon: Percent, cls: "text-accent", t: "analog.read2t", d: "analog.read2d" },
  { icon: CalendarClock, cls: "text-muted", t: "analog.read3t", d: "analog.read3d" },
] as const;

export default function AnalogsPage() {
  const { t, lang } = useI18n();
  const [q, setQ] = useState("");
  const [data, setData] = useState<AnalogResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [recent, setRecent] = useState<NewsItem[]>([]);

  useEffect(() => {
    getTopImpact(6).then(setRecent);
  }, []);

  async function run(query: string) {
    const text = query.trim();
    if (!text) return;
    setQ(text);
    setSearched(true);
    setLoading(true);
    setData(null);
    setData(await searchAnalogs(text, lang));
    setLoading(false);
  }

  // Real xəbər — saxlanmış embedding ilə daha dəqiq analoq.
  async function runNews(n: NewsItem) {
    setQ(localizedNews(n, lang).title);
    setSearched(true);
    setLoading(true);
    setData(null);
    setData(await getNewsAnalogs(n.id, lang));
    setLoading(false);
  }

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-5 py-8 flex-1">
        <div className="mb-1.5 flex items-center gap-2">
          <History size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("analog.pageTitle")}
          </h1>
        </div>
        <p className="mb-5 text-sm text-muted">{t("analog.pageSubtitle")}</p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(q);
          }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("analog.searchPlaceholder")}
              className="w-full rounded-xl border border-border bg-surface py-2.5 pl-9 pr-3 text-sm outline-none transition-colors focus:border-accent/50"
            />
          </div>
          <button
            type="submit"
            className="rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-black transition-opacity hover:brightness-110 disabled:opacity-50"
            disabled={!q.trim()}
          >
            {t("analog.search")}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted/70">
            {t("analog.tryLabel")}
          </span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.key}
              onClick={() => run(ex.q)}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted transition-colors hover:border-accent/40 hover:text-text"
            >
              {t(ex.key)}
            </button>
          ))}
        </div>

        {searched ? (
          <AnalogPanel data={data} loading={loading} />
        ) : (
          <>
            {/* Nəticəni necə oxu — istifadəçiyə yönəlik leqenda */}
            <section className="mt-8">
              <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-accent">
                {t("analog.readTitle")}
              </h2>
              <div className="grid gap-3 sm:grid-cols-3">
                {LEGEND.map((s) => {
                  const Icon = s.icon;
                  return (
                    <div
                      key={s.t}
                      className="rounded-xl border border-border bg-surface p-4"
                    >
                      <Icon size={18} className={`mb-2.5 ${s.cls}`} />
                      <h3 className="text-sm font-semibold">{t(s.t)}</h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted">
                        {t(s.d)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Son yüksək təsirli xəbərlər — bir kliklə analoq */}
            {recent.length > 0 && (
              <section className="mt-8">
                <div className="mb-1 flex items-center gap-2">
                  <History size={16} className="text-accent" />
                  <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
                    {t("analog.recent")}
                  </h2>
                </div>
                <p className="mb-3 text-sm text-muted">{t("analog.recentHint")}</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {recent.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => runNews(n)}
                      className="group flex flex-col gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/50"
                    >
                      <NewsBadges sentiment={n.sentiment} impact={n.impactScore} />
                      <p className="line-clamp-2 text-[13px] font-medium leading-snug text-text">
                        {localizedNews(n, lang).title}
                      </p>
                      <span className="mt-auto truncate font-mono text-[11px] text-muted">
                        {n.source ?? "—"}
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
