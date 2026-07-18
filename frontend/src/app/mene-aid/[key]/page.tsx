"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { Sparkline } from "@/components/charts/Sparkline";
import { NewsCard } from "@/components/news/NewsCard";
import { WatchButton } from "@/components/assets/WatchButton";
import { getAssetIntel } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssetDigest } from "@/types";

/** "Mənə Aid" drill-down — tək aktivə toxunan bütün son xəbərlər + əhval trendi. */
export default function MeneAidAssetPage() {
  const { t } = useI18n();
  const params = useParams<{ key: string }>();
  const key = params.key;

  const [data, setData] = useState<AssetDigest | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty">("loading");

  useEffect(() => {
    let alive = true;
    setStatus("loading");
    getAssetIntel(key).then((d) => {
      if (!alive) return;
      setData(d);
      setStatus(d && d.count > 0 ? "ready" : "empty");
    });
    return () => {
      alive = false;
    };
  }, [key]);

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell flex-1 py-8">
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-accent"
        >
          <ArrowLeft size={15} /> {t("meneAid.back")}
        </Link>

        {status === "loading" && (
          <div className="h-24 animate-pulse rounded-card bg-surface-hover" />
        )}

        {status === "empty" && (
          <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border py-20 text-center">
            <p className="text-base font-medium text-text">
              {data?.label ?? key.toUpperCase()}
            </p>
            <p className="mt-1.5 max-w-sm text-sm text-muted">
              {t("meneAid.emptyHint")}
            </p>
          </div>
        )}

        {status === "ready" && data && (
          <>
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
                    {t("meneAid.eyebrow")}
                  </p>
                  <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                    {data.label}
                  </h1>
                  <p className="mt-1 text-sm text-muted">
                    {data.count} {t("meneAid.itemsFull")}
                    {data.sinceCount > 0 && (
                      <>
                        {" · "}
                        <span className="text-accent">
                          +{data.sinceCount} {t("meneAid.new")}
                        </span>
                      </>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {data.sentimentTrend.length >= 2 && (
                  <div className="flex flex-col items-end gap-1">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                      {t("meneAid.mood")}
                    </span>
                    <Sparkline values={data.sentimentTrend} width={128} height={36} />
                  </div>
                )}
                <WatchButton assetKey={key} />
              </div>
            </div>

            <TrustBadgeRow trust={data.trust} t={t} />

            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 3xl:grid-cols-5">
              {data.news.map((n) => (
                <NewsCard key={n.id} news={n} />
              ))}
            </div>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}

/** Proqnoz doğruluq nişanı — Faza C-də dolur; null olduqda görünmür. */
function TrustBadgeRow({
  trust,
  t,
}: {
  trust: AssetDigest["trust"];
  t: (k: string) => string;
}) {
  if (!trust) return null;
  const good = trust.delta >= 0;
  return (
    <div className="mb-5 inline-flex items-center gap-2 rounded-card border border-border bg-surface px-3.5 py-2 text-sm">
      <span className="text-muted">{t("meneAid.trust")}</span>
      <span className="font-mono font-semibold text-text">
        {Math.round(trust.hitRate * 100)}%
      </span>
      <span className={`font-mono text-xs ${good ? "text-up" : "text-down"}`}>
        {good ? "+" : ""}
        {Math.round(trust.delta * 100)}pt {t("meneAid.vsBase")}
      </span>
      <span className="text-[11px] text-muted">
        · +{trust.horizon}
        {t("meneAid.day")} · n={trust.n}
      </span>
    </div>
  );
}
