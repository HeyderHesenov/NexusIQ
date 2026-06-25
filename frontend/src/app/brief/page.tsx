"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { Footer } from "@/components/layout/Footer";
import { useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Activity,
  Info,
} from "lucide-react";
import { getBrief, type Brief } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const DIRC: Record<string, { cls: string; Icon: typeof TrendingUp }> = {
  up: { cls: "text-emerald-400", Icon: TrendingUp },
  down: { cls: "text-rose-400", Icon: TrendingDown },
  mixed: { cls: "text-amber-400", Icon: Activity },
};

// Ssenari kartı üçün statik siniflər (Tailwind dinamik sinifləri purge edir).
const SCEN: Record<string, { wrap: string; cls: string; Icon: typeof TrendingUp }> = {
  up: { wrap: "border-emerald-500/25 bg-emerald-500/[0.05]", cls: "text-emerald-400", Icon: TrendingUp },
  down: { wrap: "border-rose-500/25 bg-rose-500/[0.05]", cls: "text-rose-400", Icon: TrendingDown },
  mixed: { wrap: "border-amber-500/25 bg-amber-500/[0.05]", cls: "text-amber-400", Icon: Activity },
};

function BriefView() {
  const { t, lang } = useI18n();
  const sp = useSearchParams();
  const kind = sp.get("kind") ?? "event";
  const name = sp.get("name") ?? "";
  const sym = sp.get("sym") ?? "";
  const meta = sp.get("meta") ?? "";
  const badge = sp.get("badge") ?? "";
  const sub = sp.get("sub") ?? "";
  const forecast = sp.get("forecast") ?? "";
  const previous = sp.get("previous") ?? "";

  const [brief, setBrief] = useState<Brief | null>(null);

  useEffect(() => {
    if (!name.trim()) {
      setBrief({ ready: false }); // hadisə seçilməyib — etibarsız sorğu atma
      return;
    }
    let alive = true;
    setBrief(null);
    getBrief(kind, name, sym, meta, lang).then((d) => alive && setBrief(d));
    return () => {
      alive = false;
    };
  }, [kind, name, sym, meta, lang]);

  return (
    <div className="flex min-h-screen flex-col">
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

      <main className="mx-auto w-full max-w-3xl px-5 py-8">
        {/* meta */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {badge && (
            <span className="rounded-md bg-accent/15 px-2.5 py-1 font-mono font-semibold uppercase tracking-wider text-accent">
              {badge}
            </span>
          )}
          {sub && <span className="font-mono text-muted">{sub}</span>}
        </div>

        <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          {name}
        </h1>

        {(forecast || previous) && (
          <div className="mt-5 flex flex-wrap gap-3">
            {forecast && <Stat label={t("market.fc")} value={forecast} />}
            {previous && <Stat label={t("market.prev")} value={previous} />}
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
            <p className="pt-1 text-xs text-muted">{t("brief.loading")}</p>
          </div>
        )}

        {brief && !brief.ready && (
          <p className="mt-8 rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-muted">
            {t("brief.none")}
          </p>
        )}

        {brief?.ready && (
          <>
            <Section icon={<Info size={16} className="text-accent" />} title={t("brief.what")}>
              <p className="text-[15px] leading-relaxed text-text/90">{brief.what}</p>
            </Section>

            {/* ssenarilər (AI etiketləri ilə) */}
            {brief.scenarios && brief.scenarios.length > 0 && (
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {brief.scenarios.map((s, i) => {
                  const { wrap, cls, Icon } = SCEN[s.dir] ?? SCEN.mixed;
                  return (
                    <div key={i} className={`rounded-card border p-4 ${wrap}`}>
                      <div className="mb-2 flex items-center gap-1.5">
                        <Icon size={15} className={cls} />
                        <h3
                          className={`font-mono text-[11px] uppercase tracking-[0.15em] ${cls}`}
                        >
                          {s.label}
                        </h3>
                      </div>
                      <p className="text-[14px] leading-relaxed text-text/85">{s.text}</p>
                    </div>
                  );
                })}
              </div>
            )}

            {/* təsirlənən instrumentlər */}
            {brief.pairs && brief.pairs.length > 0 && (
              <Section
                icon={<TrendingUp size={16} className="text-accent" />}
                title={
                  brief.pairsNote
                    ? `${t("brief.pairs")} · ${brief.pairsNote}`
                    : t("brief.pairs")
                }
              >
                <ul className="space-y-2.5">
                  {brief.pairs.map((p, i) => {
                    const { cls, Icon } = DIRC[p.bias] ?? DIRC.mixed;
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
      <Footer />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-2.5">
      <p className="font-mono text-[11px] uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-0.5 font-mono text-lg font-semibold text-text">{value}</p>
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
        <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-accent">{title}</h2>
      </div>
      {children}
    </section>
  );
}

export default function BriefPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <BriefView />
    </Suspense>
  );
}
