"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { LineChart } from "@/components/charts/LineChart";
import { NewsImage } from "@/components/news/NewsImage";
import { WatchButton } from "@/components/assets/WatchButton";
import { getAssetDetail, getAssetNews, type AssetNewsItem } from "@/lib/api";
import { addAlert } from "@/lib/alerts";
import { warmRoute } from "@/lib/prewarm";
import { formatDateTime } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { AssetDetail } from "@/types";

const RANGES = ["1mo", "3mo", "6mo", "1y"];

export default function AssetPage() {
  const { t } = useI18n();
  const params = useParams<{ key: string }>();
  const key = params.key;

  const [range, setRange] = useState("3mo");
  const [data, setData] = useState<AssetDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [refreshing, setRefreshing] = useState(false);
  const [news, setNews] = useState<AssetNewsItem[]>([]);

  // İlk yükləmə (yeni aktiv) → tam skeleton; sadəcə dövr dəyişimi → yumşaq
  // refresh (səhifə skeleton-a çevrilib donmasın, cari qrafik qalsın).
  const firstForKey = useRef(true);
  useEffect(() => {
    firstForKey.current = true;
  }, [key]);

  const load = useCallback(
    (r: string) => {
      if (firstForKey.current) setStatus("loading");
      else setRefreshing(true);
      getAssetDetail(key, r).then((d) => {
        setData(d);
        setStatus(d && (d.quote || d.history) ? "ready" : "error");
        setRefreshing(false);
        firstForKey.current = false;
      });
    },
    [key],
  );

  useEffect(() => {
    load(range);
  }, [range, load]);

  useEffect(() => {
    getAssetNews(key).then(setNews);
  }, [key]);

  const q = data?.quote;
  const h = data?.history;
  const chgColor = q ? (q.up ? "text-up" : "text-down") : "text-muted";

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell py-8 flex-1">
        {status === "loading" && (
          <div className="h-72 animate-pulse rounded-card bg-surface-hover" />
        )}
        {status === "error" && (
          <p className="py-20 text-center text-sm text-muted">
            {t("asset.notFound")}
          </p>
        )}
        {status === "ready" && (
          <>
            {/* başlıq */}
            <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">
                    {q?.label ?? key}
                  </h1>
                  {q && (
                    <div className="mt-1 flex items-baseline gap-3">
                      <span className="font-mono text-xl">{q.val}</span>
                      <span className={`font-mono text-sm ${chgColor}`}>
                        {q.chg}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <WatchButton assetKey={key} />
            </div>

            {/* dövr seçimi */}
            <div className="mb-4 flex gap-1 rounded-xl border border-border bg-surface p-1 w-fit">
              {RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={`rounded-lg px-3 py-1 text-sm font-medium transition-all ${
                    range === r ? "bg-accent text-black" : "text-muted hover:text-text"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>

            {/* qrafik — dövr dəyişəndə cari qrafik qalır, sadəcə solğunlaşır */}
            <section className="relative rounded-card border border-border bg-surface p-5">
              <div className={refreshing ? "opacity-40 transition-opacity" : "transition-opacity"}>
                {h && h.points.length > 1 ? (
                  <LineChart
                    series={[
                      {
                        label: h.label,
                        color: "#ff7a1a",
                        points: h.points.map((p) => ({
                          date: p.date,
                          value: p.close,
                        })),
                      },
                    ]}
                  />
                ) : (
                  <p className="py-12 text-center text-sm text-muted">—</p>
                )}
              </div>
              {refreshing && (
                <span className="absolute right-4 top-4 h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
              )}
            </section>

            {/* sürətli siqnal */}
            {q && <QuickAlert assetKey={key} label={q.label} price={q.price} />}

            {/* əlaqəli xəbərlər — DB-first, boşluqda Yahoo ehtiyatı */}
            {news.length > 0 && (
              <section className="mt-8">
                <h2 className="mb-4 text-sm font-semibold">
                  {t("asset.relatedNews")}
                </h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {news.map((n, i) => (
                    <RelatedNewsItem key={n.id ?? n.url ?? i} news={n} />
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

/**
 * Əlaqəli xəbər sətri. Örtük `NewsImage`-dən gəlir — real şəkil yoxdursa,
 * qırıqdırsa və ya boş yüklənirsə brendli örtük görünür (boş qutu OLMUR).
 * DB xəbəri (`id` var) daxili SPA linkidir; Yahoo ehtiyat xəbəri xaricidir.
 */
function RelatedNewsItem({ news: n }: { news: AssetNewsItem }) {
  const router = useRouter();
  const cls =
    "group flex gap-3 rounded-card border border-border bg-surface p-3 transition-all hover:-translate-y-0.5 hover:border-accent/40";
  const body = (
    <>
      <NewsImage
        src={n.imageUrl}
        seed={n.id ?? n.url ?? n.title}
        category={n.category}
        className="h-16 w-24 shrink-0 rounded-lg"
        compact
        newsId={n.id}
        width={192}
      />
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-medium leading-snug group-hover:text-accent">
          {n.title}
        </p>
        <p className="mt-1.5 truncate font-mono text-[11px] text-muted">
          {n.source ?? "—"}
          {n.publishedAt ? ` · ${formatDateTime(n.publishedAt)}` : ""}
        </p>
      </div>
    </>
  );

  if (n.id) {
    const href = `/news/${n.id}`;
    return (
      <Link
        href={href}
        onMouseEnter={() => warmRoute(router, href)}
        onFocus={() => warmRoute(router, href)}
        className={cls}
      >
        {body}
      </Link>
    );
  }
  return (
    <a href={n.url ?? "#"} target="_blank" rel="noopener noreferrer" className={cls}>
      {body}
    </a>
  );
}

/** Bu aktiv üçün sürətli qiymət siqnalı yaratma. */
function QuickAlert({
  assetKey,
  label,
  price,
}: {
  assetKey: string;
  label: string;
  price: number;
}) {
  const { t } = useI18n();
  const [value, setValue] = useState(String(price));
  const [dir, setDir] = useState<"above" | "below">("above");
  const [done, setDone] = useState(false);

  function create() {
    const p = parseFloat(value);
    if (!Number.isFinite(p)) return;
    addAlert({ key: assetKey, label, direction: dir, price: p });
    setDone(true);
    window.setTimeout(() => setDone(false), 2500);
  }

  return (
    <section className="mt-6 rounded-card border border-border bg-surface p-4">
      <h2 className="mb-3 text-sm font-semibold">{t("alert.quickTitle")}</h2>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-1 rounded-lg border border-border bg-bg p-1">
          {(["above", "below"] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDir(d)}
              className={`rounded-md px-3 py-1 text-sm transition-all ${
                dir === d ? "bg-accent text-black" : "text-muted hover:text-text"
              }`}
            >
              {d === "above" ? t("alert.above") : t("alert.below")}
            </button>
          ))}
        </div>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          inputMode="decimal"
          className="w-36 rounded-lg border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none"
        />
        <button
          onClick={create}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-black transition-opacity hover:brightness-110"
        >
          {t("alert.create")}
        </button>
        {done && <span className="text-sm text-up">{t("alert.created")}</span>}
      </div>
    </section>
  );
}
