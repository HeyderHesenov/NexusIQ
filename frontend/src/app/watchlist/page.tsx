"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, Star } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { WatchButton } from "@/components/assets/WatchButton";
import { AssetPicker } from "@/components/assets/AssetPicker";
import { Sparkline } from "@/components/charts/Sparkline";
import { getAssets, getAssetDetail, getAssetsOverview } from "@/lib/api";
import { toggleWatch, useWatchlist } from "@/lib/watchlist";
import { useI18n } from "@/lib/i18n";
import type { Asset, AssetDetail, AssetOverview, AssetType } from "@/types";

/** Açılan tam siyahıda kateqoriya sırası. */
const TYPE_ORDER: AssetType[] = ["crypto", "forex", "index", "commodity", "metal"];

/** Səhifə boş görünməsin deyə nümunə populyar aktivlər — bir kliklə əlavə. */
const SAMPLE_KEYS = [
  "btc",
  "eth",
  "xrp",
  "eurusd",
  "gbpusd",
  "usdjpy",
  "dxy",
  "ndx",
  "spx",
  "dji",
];

export default function WatchlistPage() {
  const { t } = useI18n();
  const watched = useWatchlist();
  const [registry, setRegistry] = useState<Asset[]>([]);
  const [details, setDetails] = useState<Record<string, AssetDetail>>({});

  useEffect(() => {
    getAssets().then(setRegistry);
  }, []);

  useEffect(() => {
    if (watched.length === 0) return;
    let stop = false;
    async function load() {
      const ds = await Promise.all(watched.map((k) => getAssetDetail(k, "1mo")));
      if (stop) return;
      const map: Record<string, AssetDetail> = {};
      watched.forEach((k, i) => {
        const d = ds[i];
        if (d) map[k] = d;
      });
      setDetails(map);
    }
    load();
    const id = window.setInterval(load, 60_000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, [watched]);


  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto max-w-7xl px-5 py-8">
        <div className="mb-6 flex items-center gap-2">
          <Star size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("nav.watchlist")}
          </h1>
        </div>

        {watched.length === 0 ? (
          <p className="rounded-card border border-dashed border-border py-16 text-center text-sm text-muted">
            {t("watch.empty")}
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {watched.map((k) => {
              const d = details[k];
              const q = d?.quote;
              const closes = d?.history?.points.map((p) => p.close) ?? [];
              return (
                <div
                  key={k}
                  className="group rounded-card border border-border bg-surface p-4 transition-colors hover:border-accent/40"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Link href={`/asset/${k}`} className="min-w-0">
                      <p className="truncate font-semibold">
                        {q?.label ?? k.replace(/^c_/, "").toUpperCase()}
                      </p>
                    </Link>
                    <WatchButton assetKey={k} />
                  </div>
                  <Link
                    href={`/asset/${k}`}
                    className="mt-3 flex items-end justify-between gap-3"
                  >
                    <div>
                      {q ? (
                        <>
                          <p className="font-mono text-base">{q.val}</p>
                          <p
                            className={`font-mono text-xs ${q.up ? "text-up" : "text-down"}`}
                          >
                            {q.chg}
                          </p>
                        </>
                      ) : (
                        <div className="h-8 w-20 animate-pulse rounded bg-surface-hover" />
                      )}
                    </div>
                    {closes.length > 1 && <Sparkline values={closes} />}
                  </Link>
                </div>
              );
            })}
          </div>
        )}

        {/* aktiv idarəetmə — axtarışlı seçici */}
        {registry.length > 0 && (
          <section className="mt-8">
            <h2 className="mb-3 text-sm font-semibold">{t("watch.addTitle")}</h2>
            <AssetPicker
              assets={registry}
              isSelected={(k) => watched.includes(k)}
              onToggle={toggleWatch}
            />
          </section>
        )}

        {/* populyar nümunələr — səhifəni doldurur, sürətli əlavə */}
        <PopularAssets />
      </main>
      <Footer />
    </div>
  );
}

/** Populyar aktivlər — CoinMarketCap üslublu cədvəl + açılan tam kateqoriyalı siyahı. */
function PopularAssets() {
  const { t } = useI18n();
  const [all, setAll] = useState<AssetOverview[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let stop = false;
    getAssetsOverview().then((d) => {
      if (!stop) setAll(d);
    });
    return () => {
      stop = true;
    };
  }, []);

  const byKey = new Map(all.map((r) => [r.key, r]));
  const popular = SAMPLE_KEYS.map((k) => byKey.get(k)).filter(
    Boolean,
  ) as AssetOverview[];

  // tam siyahını kateqoriyaya görə qrupla (sıra: TYPE_ORDER)
  const groups = TYPE_ORDER.map((type) => ({
    type,
    rows: all.filter((r) => r.type === type),
  })).filter((g) => g.rows.length > 0);

  return (
    <section className="mt-10">
      <h2 className="text-sm font-semibold">{t("watch.popular")}</h2>
      <p className="mb-3 mt-1 text-xs text-muted">{t("watch.popularHint")}</p>

      <div className="overflow-hidden rounded-card border border-border">
        <table className="w-full text-sm">
          <AssetTableHead />
          <tbody>
            {popular.length === 0
              ? SAMPLE_KEYS.map((k) => <SkeletonRow key={k} />)
              : popular.map((r, i) => (
                  <AssetRow key={r.key} row={r} rank={i + 1} />
                ))}
          </tbody>
        </table>

        {/* aşağı strelka — tam kateqoriyalı siyahını aç/bağla */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex w-full items-center justify-center gap-2 border-t border-border bg-surface py-2.5 text-xs font-medium text-muted transition-colors hover:bg-surface-hover hover:text-accent"
        >
          {expanded ? t("watch.hideAll") : t("watch.showAll")}
          <ChevronDown
            size={15}
            className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {/* açılan kateqoriyalı tam siyahı */}
      {expanded && (
        <div className="fade-up mt-4 space-y-6">
          {groups.map((g) => (
            <div key={g.type}>
              <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-muted">
                {t(`atype.${g.type}`)}
                <span className="ml-2 text-muted">{g.rows.length}</span>
              </p>
              <div className="overflow-hidden rounded-card border border-border">
                <table className="w-full text-sm">
                  <AssetTableHead />
                  <tbody>
                    {g.rows.map((r, i) => (
                      <AssetRow key={r.key} row={r} rank={i + 1} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/** CMC cədvəl başlığı — populyar və qruplarda təkrar istifadə. */
function AssetTableHead() {
  const { t } = useI18n();
  return (
    <thead className="border-b border-border bg-surface text-muted">
      <tr>
        <th className="w-10 px-3 py-3 text-right font-medium">#</th>
        <th className="px-3 py-3 text-left font-medium">{t("assets.name")}</th>
        <th className="px-3 py-3 text-right font-medium">{t("assets.price")}</th>
        <th className="px-3 py-3 text-right font-medium">24s</th>
        <th className="hidden px-3 py-3 text-right font-medium sm:table-cell">7g</th>
        <th className="w-12 px-3 py-3" />
      </tr>
    </thead>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-t border-border">
      <td colSpan={6} className="px-3 py-3">
        <div className="h-6 w-full animate-pulse rounded bg-surface-hover" />
      </td>
    </tr>
  );
}

/** Bir CMC sətri — rank, ad, qiymət, 24s, sparkline, izlə düyməsi. */
function AssetRow({ row, rank }: { row: AssetOverview; rank: number }) {
  return (
    <tr className="group border-t border-border transition-colors hover:bg-surface-hover">
      <td className="px-3 py-2.5 text-right font-mono text-xs text-muted">{rank}</td>
      <td className="px-3 py-2.5">
        <Link href={`/asset/${row.key}`} className="font-medium hover:text-accent">
          {row.label}
        </Link>
      </td>
      <td className="px-3 py-2.5 text-right font-mono">{row.val}</td>
      <td
        className={`px-3 py-2.5 text-right font-mono text-xs ${row.up ? "text-up" : "text-down"}`}
      >
        {row.chg}
      </td>
      <td className="hidden px-3 py-2.5 sm:table-cell">
        <div className="flex justify-end">
          <Sparkline values={row.spark} width={104} height={32} />
        </div>
      </td>
      <td className="px-2 py-2.5">
        <WatchButton assetKey={row.key} />
      </td>
    </tr>
  );
}
