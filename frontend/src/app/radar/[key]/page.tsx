"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, Github, Globe, Radar, Sparkles } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { ScoreBars, ScoreRing, themeLabel } from "@/components/radar/RadarVisuals";
import { getRadarDetail, getRadarExplain, streamRadarAbout } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { RadarDetail } from "@/types";

/** Tam enli sahə qrafiki (7g/1ay sparkline datasından), trendə görə rəngli. */
function DetailChart({ values }: { values: number[] }) {
  if (!values || values.length < 2) return null;
  const W = 100;
  const H = 32;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i: number) => (i / (values.length - 1)) * W;
  const y = (v: number) => H - ((v - min) / span) * H;
  const line = values
    .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(2)},${y(v).toFixed(2)}`)
    .join(" ");
  const area = `${line} L${W},${H} L0,${H} Z`;
  const up = values[values.length - 1] >= values[0];
  const cls = up ? "text-up" : "text-down";
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className={`h-36 w-full ${cls}`}
      aria-hidden
    >
      <defs>
        <linearGradient id="rd-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.2" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#rd-area)" />
      <path
        d={line}
        fill="none"
        stroke="currentColor"
        strokeWidth="0.6"
        vectorEffect="non-scaling-stroke"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-surface px-3.5 py-2.5">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-0.5 font-mono text-sm font-semibold ${accent ? "text-up" : ""}`}>
        {value}
      </div>
    </div>
  );
}

export default function RadarDetailPage() {
  const { t, lang } = useI18n();
  const { key } = useParams<{ key: string }>();
  const [d, setD] = useState<RadarDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const [explain, setExplain] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [asked, setAsked] = useState(false);

  // "Haqqında" — seçilmiş dildə ətraflı AI icmalı (avto-yüklə, keşli).
  const [about, setAbout] = useState<string | null>(null);
  const [aboutLoading, setAboutLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getRadarDetail(key).then((data) => {
      if (cancelled) return;
      setD(data);
      setStatus(data ? "ready" : "error");
    });
    return () => {
      cancelled = true;
    };
  }, [key]);

  useEffect(() => {
    const ctrl = new AbortController();
    let cancelled = false;
    setAboutLoading(true);
    setAbout(null);
    let acc = "";
    streamRadarAbout(
      key,
      lang,
      (delta) => {
        if (cancelled) return;
        acc += delta;
        setAboutLoading(false);
        setAbout(acc);
      },
      ctrl.signal,
    ).finally(() => {
      if (!cancelled) setAboutLoading(false);
    });
    return () => {
      cancelled = true;
      ctrl.abort(); // dil/coin dəyişəndə köhnə axını dayandır (GPT israfı yox)
    };
  }, [key, lang]);

  const onExplain = useCallback(async () => {
    setExplaining(true);
    setAsked(true);
    const text = await getRadarExplain(key, lang);
    setExplain(text);
    setExplaining(false);
  }, [key, lang]);

  const tag = d && (d.type === "crypto" ? d.category : d.theme && themeLabel(d.theme));

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-5 py-8">
        <Link
          href="/radar"
          className="mb-5 inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-text"
        >
          <ArrowLeft size={15} />
          {t("radar.back")}
        </Link>

        {status === "loading" && (
          <div className="space-y-4">
            <div className="h-28 animate-pulse rounded-card border border-border bg-surface" />
            <div className="h-44 animate-pulse rounded-card border border-border bg-surface" />
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center justify-center rounded-card border border-border bg-surface py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-border">
              <Radar size={22} className="text-muted" />
            </div>
            <p className="text-sm text-muted">{t("radar.notFound")}</p>
          </div>
        )}

        {status === "ready" && d && (
          <div className="space-y-5">
            {/* başlıq */}
            <div className="flex items-center gap-4 rounded-card border border-border bg-surface p-5">
              <ScoreRing score={d.score} size={96} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <h1 className="text-xl font-semibold tracking-tight">{d.label}</h1>
                  {tag && (
                    <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                      {tag}
                    </span>
                  )}
                </div>
                {d.name && d.name !== d.label && (
                  <p className="mt-0.5 truncate text-sm text-muted">{d.name}</p>
                )}
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">{d.val}</span>
                  <span
                    className={`font-mono text-sm tabular-nums ${d.up ? "text-up" : "text-down"}`}
                  >
                    {d.chg}
                  </span>
                </div>
              </div>
            </div>

            {/* statlar */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Stat label={t("radar.mc")} value={d.mcapFmt} />
              {d.revenueFmt && <Stat label={t("radar.rev")} value={d.revenueFmt} accent />}
              {tag && <Stat label={t(`radar.tab.${d.tab}`)} value={tag} />}
            </div>

            {/* qrafik + bal komponentləri */}
            <div className="rounded-card border border-border bg-surface p-5">
              <DetailChart values={d.spark} />
              <div className="mt-5">
                <ScoreBars breakdown={d.breakdown} />
              </div>
            </div>

            {/* AI izah */}
            <div className="rounded-card border border-border bg-surface p-5">
              {asked ? (
                <p className="flex items-start gap-2 text-sm text-text">
                  <Sparkles size={15} className="mt-0.5 shrink-0 text-accent" />
                  <span>
                    {explaining ? t("radar.explaining") : explain || t("radar.noExplain")}
                  </span>
                </p>
              ) : (
                <button
                  onClick={onExplain}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-accent transition-opacity hover:opacity-80"
                >
                  <Sparkles size={15} />
                  {t("radar.explain")}
                </button>
              )}
            </div>

            {/* haqqında — yalnız seçilmiş dildə AI icmalı (ingiliscə fallback yox) */}
            {(aboutLoading || about) && (
              <div className="rounded-card border border-border bg-surface p-5">
                <h2 className="mb-3 text-sm font-semibold">{t("radar.about")}</h2>
                {aboutLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <div
                        key={i}
                        className={`h-3.5 animate-pulse rounded bg-surface-hover ${
                          i === 3 ? "w-2/3" : "w-full"
                        }`}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3 text-sm leading-relaxed text-muted">
                    {about!.split(/\n+/).filter(Boolean).map((para, i) => (
                      <p key={i}>{para}</p>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* linklər — opensource ən sonda */}
            <div className="rounded-card border border-border bg-surface p-5">
              <h2 className="mb-3 text-sm font-semibold">{t("radar.links")}</h2>
              <div className="flex flex-col gap-2">
                {d.homepage && (
                  <LinkRow href={d.homepage} icon={<Globe size={15} />} label={t("radar.website")} />
                )}
                {d.link && (
                  <LinkRow href={d.link} icon={<ExternalLink size={15} />} label={t("radar.source")} />
                )}
                {d.github && (
                  <LinkRow href={d.github} icon={<Github size={15} />} label={t("radar.opensource")} />
                )}
              </div>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}

function LinkRow({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-between rounded-xl border border-border px-3.5 py-2.5 text-sm transition-colors hover:bg-surface-hover hover:text-accent"
    >
      <span className="flex items-center gap-2.5">
        <span className="text-muted">{icon}</span>
        {label}
      </span>
      <ExternalLink size={13} className="text-muted" />
    </a>
  );
}
