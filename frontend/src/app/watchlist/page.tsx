"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Star } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { WatchButton } from "@/components/assets/WatchButton";
import { AssetPicker } from "@/components/assets/AssetPicker";
import { Sparkline } from "@/components/charts/Sparkline";
import { getAssets, getAssetDetail, getAssetsOverview } from "@/lib/api";
import { toggleWatch, useWatchlist } from "@/lib/watchlist";
import { useI18n } from "@/lib/i18n";
import type { Asset, AssetDetail, AssetOverview } from "@/types";

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

/** Populyar aktivlər — CoinMarketCap üslublu cədvəl, bir kliklə izləməyə. */
function PopularAssets() {
  const { t } = useI18n();
  const [rows, setRows] = useState<AssetOverview[]>([]);

  useEffect(() => {
    let stop = false;
    getAssetsOverview().then((all) => {
      if (stop) return;
      const byKey = new Map(all.map((r) => [r.key, r]));
      setRows(SAMPLE_KEYS.map((k) => byKey.get(k)).filter(Boolean) as AssetOverview[]);
    });
    return () => {
      stop = true;
    };
  }, []);

  return (
    <section className="mt-10">
      <h2 className="text-sm font-semibold">{t("watch.popular")}</h2>
      <p className="mb-3 mt-1 text-xs text-muted">{t("watch.popularHint")}</p>
      <div className="overflow-hidden rounded-card border border-border">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-surface text-muted">
            <tr>
              <th className="w-10 px-3 py-3 text-right font-medium">#</th>
              <th className="px-3 py-3 text-left font-medium">{t("assets.name")}</th>
              <th className="px-3 py-3 text-right font-medium">{t("assets.price")}</th>
              <th className="px-3 py-3 text-right font-medium">24s</th>
              <th className="hidden px-3 py-3 text-right font-medium sm:table-cell">
                7g
              </th>
              <th className="w-12 px-3 py-3" />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 &&
              SAMPLE_KEYS.map((k) => (
                <tr key={k} className="border-t border-border">
                  <td colSpan={6} className="px-3 py-3">
                    <div className="h-6 w-full animate-pulse rounded bg-surface-hover" />
                  </td>
                </tr>
              ))}

            {rows.map((r, i) => (
              <tr
                key={r.key}
                className="group border-t border-border transition-colors hover:bg-surface-hover"
              >
                <td className="px-3 py-2.5 text-right font-mono text-xs text-muted">
                  {i + 1}
                </td>
                <td className="px-3 py-2.5">
                  <Link
                    href={`/asset/${r.key}`}
                    className="font-medium hover:text-accent"
                  >
                    {r.label}
                  </Link>
                </td>
                <td className="px-3 py-2.5 text-right font-mono">{r.val}</td>
                <td
                  className={`px-3 py-2.5 text-right font-mono text-xs ${r.up ? "text-up" : "text-down"}`}
                >
                  {r.chg}
                </td>
                <td className="hidden px-3 py-2.5 sm:table-cell">
                  <div className="flex justify-end">
                    <Sparkline values={r.spark} width={104} height={32} />
                  </div>
                </td>
                <td className="px-2 py-2.5">
                  <WatchButton assetKey={r.key} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
