"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Activity,
  Info,
} from "lucide-react";
import { getEventBrief, type EventBrief } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const BIAS: Record<string, { cls: string; Icon: typeof TrendingUp }> = {
  up: { cls: "text-emerald-400", Icon: TrendingUp },
  down: { cls: "text-rose-400", Icon: TrendingDown },
  mixed: { cls: "text-amber-400", Icon: Activity },
};

function EventView() {
  const { t, lang } = useI18n();
  const sp = useSearchParams();
  const title = sp.get("title") ?? "";
  const country = sp.get("country") ?? "";
  const impact = sp.get("impact") ?? "";
  const date = sp.get("date") ?? "";
  const time = sp.get("time") ?? "";
  const forecast = sp.get("forecast") ?? "";
  const previous = sp.get("previous") ?? "";

  const [brief, setBrief] = useState<EventBrief | null>(null);

  useEffect(() => {
    let alive = true;
    setBrief(null);
    getEventBrief(title, country, impact, lang).then(
      (d) => alive && setBrief(d),
    );
    return () => {
      alive = false;
    };
  }, [title, country, impact, lang]);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-5">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-muted transition-colors hover:text-text"
          >
            <ArrowLeft size={18} />
            {t("news.back")}
          </Link>
          <span className="text-sm font-semibold tracking-tight">
            Nexus<span className="text-accent">IQ</span>
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-8">
        {/* meta */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {country && (
            <span className="rounded-md bg-surface-hover px-2.5 py-1 font-mono font-semibold uppercase tracking-wider text-text/80">
              {country}
            </span>
          )}
          {impact && (
            <span className="flex items-center gap-1.5 font-mono text-muted">
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  impact === "High" ? "bg-rose-400" : "bg-amber-400"
                }`}
              />
              {impact}
            </span>
          )}
          {(date || time) && (
            <span className="font-mono text-muted">
              {date} {time}
            </span>
          )}
        </div>

        <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          {title}
        </h1>

        {/* forecast / previous */}
        {(forecast || previous) && (
          <div className="mt-5 flex flex-wrap gap-3">
            {forecast && (
              <div className="rounded-xl border border-border bg-surface px-4 py-2.5">
                <p className="font-mono text-[11px] uppercase tracking-wider text-muted">
                  {t("market.fc")}
                </p>
                <p className="mt-0.5 font-mono text-lg font-semibold text-text">
                  {forecast}
                </p>
              </div>
            )}
            {previous && (
              <div className="rounded-xl border border-border bg-surface px-4 py-2.5">
                <p className="font-mono text-[11px] uppercase tracking-wider text-muted">
                  {t("market.prev")}
                </p>
                <p className="mt-0.5 font-mono text-lg font-semibold text-text">
                  {previous}
                </p>
              </div>
            )}
          </div>
        )}

        {/* yüklənir */}
        {!brief && (
          <div className="mt-8 space-y-3">
            {[100, 92, 80].map((w, i) => (
              <div
                key={i}
                className="h-4 animate-pulse rounded bg-surface-hover"
                style={{ width: `${w}%` }}
              />
            ))}
            <p className="pt-1 text-xs text-muted">{t("event.loading")}</p>
          </div>
        )}

        {brief && !brief.ready && (
          <p className="mt-8 rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-muted">
            {t("event.none")}
          </p>
        )}

        {brief?.ready && (
          <>
            {/* nədir */}
            <Section icon={<Info size={16} className="text-accent" />} title={t("event.what")}>
              <p className="text-[15px] leading-relaxed text-text/90">{brief.what}</p>
            </Section>

            {/* yuxarı / aşağı */}
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {brief.higher && (
                <div className="rounded-card border border-emerald-500/25 bg-emerald-500/[0.05] p-4">
                  <div className="mb-2 flex items-center gap-1.5">
                    <TrendingUp size={15} className="text-emerald-400" />
                    <h3 className="font-mono text-[11px] uppercase tracking-[0.15em] text-emerald-400">
                      {t("event.higher")}
                    </h3>
                  </div>
                  <p className="text-[14px] leading-relaxed text-text/85">{brief.higher}</p>
                </div>
              )}
              {brief.lower && (
                <div className="rounded-card border border-rose-500/25 bg-rose-500/[0.05] p-4">
                  <div className="mb-2 flex items-center gap-1.5">
                    <TrendingDown size={15} className="text-rose-400" />
                    <h3 className="font-mono text-[11px] uppercase tracking-[0.15em] text-rose-400">
                      {t("event.lower")}
                    </h3>
                  </div>
                  <p className="text-[14px] leading-relaxed text-text/85">{brief.lower}</p>
                </div>
              )}
            </div>

            {/* təsirlənən pairlər */}
            {brief.pairs && brief.pairs.length > 0 && (
              <Section
                icon={<TrendingUp size={16} className="text-accent" />}
                title={`${t("event.pairs")} · ${t("event.onHigher")}`}
              >
                <ul className="space-y-2.5">
                  {brief.pairs.map((p, i) => {
                    const { cls, Icon } = BIAS[p.bias] ?? BIAS.mixed;
                    return (
                      <li
                        key={`${p.sym}-${i}`}
                        className="flex items-start gap-3 rounded-xl border border-border bg-surface px-4 py-3"
                      >
                        <span className="mt-0.5 flex w-24 shrink-0 items-center gap-1.5 font-mono text-sm font-semibold">
                          <Icon size={15} className={cls} />
                          {p.sym}
                        </span>
                        <span className="text-[14px] leading-snug text-text/80">
                          {p.reason}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </Section>
            )}

            <p className="mt-6 text-[11px] text-muted/70">{t("news.forecastNote")}</p>
          </>
        )}
      </main>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-8">
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

export default function EventPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <EventView />
    </Suspense>
  );
}
