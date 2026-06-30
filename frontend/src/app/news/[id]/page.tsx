"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Footer } from "@/components/layout/Footer";
import { ArrowLeft, ExternalLink, Sparkles } from "lucide-react";
import { apiGet } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatDateTime, localizedNews } from "@/lib/utils";
import { NewsImage } from "@/components/news/NewsImage";
import { AIForecast } from "@/components/news/AIForecast";
import { HistoricalAnalogs } from "@/components/news/HistoricalAnalogs";
import { OriginalText } from "@/components/news/OriginalText";
import type { NewsItem } from "@/types";

export default function NewsDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const { t, lang } = useI18n();
  const [news, setNews] = useState<NewsItem | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let alive = true;
    apiGet<NewsItem>(`/news/${id}`)
      .then((d) => alive && (setNews(d), setStatus("ready")))
      .catch(() => alive && setStatus("error"));
    return () => {
      alive = false;
    };
  }, [id]);

  return (
    <div className="flex min-h-screen flex-col">
      {/* üst zolaq */}
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

      <main className="mx-auto w-full max-w-3xl px-5 py-8 flex-1">
        {status === "loading" && <DetailSkeleton />}

        {status === "error" && (
          <div className="py-24 text-center">
            <p className="text-base font-medium">{t("news.notFound")}</p>
            <Link
              href="/"
              className="mt-5 inline-block rounded-lg border border-border bg-surface px-4 py-2 text-sm transition-colors hover:border-accent hover:text-accent"
            >
              {t("news.back")}
            </Link>
          </div>
        )}

        {status === "ready" && news && (
          <article>
            {/* meta */}
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="rounded-md bg-accent/15 px-2.5 py-1 font-mono uppercase tracking-wider text-accent">
                {t(`news.cat.${news.category}`)}
              </span>
              {news.source && (
                <span className="font-medium text-muted">{news.source}</span>
              )}
              <span className="font-mono text-muted">
                {formatDateTime(news.publishedAt)}
              </span>
            </div>

            {/* başlıq */}
            <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
              {localizedNews(news, lang).title}
            </h1>

            {/* real şəkil (alınmasa generativ fallback) */}
            <div className="mt-6 aspect-[16/9] w-full overflow-hidden rounded-card border border-border bg-surface-hover">
              <NewsImage
                src={news.imageUrl}
                seed={news.id}
                category={news.category}
                className="h-full w-full"
              />
            </div>

            {/* AI xülasə bloku — oxucunun dilində qısa digest, vurğulu kart */}
            {(() => {
              const orig = (news.content ?? news.summary ?? "").trim();
              const ai = localizedNews(news, lang).body.trim();
              // Seçilmiş dildə tərcümə varsa onu göstər (isProcessed-dən asılı deyil —
              // pulsuz tərcümə body-ni doldurur, amma isProcessed false qalır).
              const hasAI = !!ai && ai !== orig;

              return (
                <>
                  {/* orijinal xəbər mətni — tam, seçilmiş dilə tərcümə */}
                  {hasAI && orig && <OriginalText id={news.id} fallback={orig} />}

                  {/* AI xülasə — oxucunun dilində qısa digest, vurğulu kart */}
                  <section className="mt-8 rounded-card border border-accent/30 bg-accent/[0.06] p-5 sm:p-6">
                    <div className="mb-3 flex items-center gap-2">
                      <Sparkles size={16} className="text-accent" />
                      <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
                        {t("news.aiSummary")}
                      </h2>
                    </div>

                    {!hasAI && lang !== "en" && (
                      <p className="mb-4 rounded-lg border border-border bg-surface px-3.5 py-2.5 text-xs text-muted">
                        {t("news.aiPending")}
                      </p>
                    )}

                    <p className="whitespace-pre-line text-[15px] leading-relaxed text-text/90">
                      {(hasAI ? ai : orig) || t("news.noBody")}
                    </p>
                  </section>

                  {/* AI bazar proqnozu — lazy yüklənir */}
                  <AIForecast id={news.id} />

                  {/* Tarixi analoqlar — bənzər keçmiş hadisələr + nəticə */}
                  <HistoricalAnalogs newsId={news.id} />
                </>
              );
            })()}

            {/* orijinal mənbə */}
            {news.originalUrl && (
              <div className="mt-10 border-t border-border pt-6">
                <p className="mb-2 text-xs text-muted">{t("news.sourceLabel")}</p>
                <a
                  href={news.originalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text transition-colors hover:border-accent hover:text-accent"
                >
                  <ExternalLink size={16} />
                  {news.source
                    ? t("news.openSource").replace("{source}", news.source)
                    : t("news.openSourceGeneric")}
                </a>
              </div>
            )}
          </article>
        )}
      </main>
      <Footer />
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-5">
      <div className="h-4 w-40 rounded bg-surface-hover" />
      <div className="h-9 w-full rounded bg-surface-hover" />
      <div className="h-9 w-3/4 rounded bg-surface-hover" />
      <div className="aspect-[16/9] w-full rounded-card bg-surface-hover" />
      <div className="h-4 w-full rounded bg-surface-hover" />
      <div className="h-4 w-5/6 rounded bg-surface-hover" />
      <div className="h-4 w-2/3 rounded bg-surface-hover" />
    </div>
  );
}
