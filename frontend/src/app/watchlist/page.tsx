"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, Star } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { WatchButton } from "@/components/assets/WatchButton";
import { AssetPicker } from "@/components/assets/AssetPicker";
import { Sparkline } from "@/components/charts/Sparkline";
import {
  AssetRow,
  AssetTableHead,
  SkeletonRow,
} from "@/components/assets/AssetTable";
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
  const [activeType, setActiveType] = useState<AssetType>("crypto");

  useEffect(() => {
    let stop = false;
    getAssetsOverview().then((d) => {
      if (!stop) setAll(d);
    });
    return () => {
      stop = true;
    };
  }, []);

  const [expanded, setExpanded] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  const byKey = new Map(all.map((r) => [r.key, r]));
  const popular = SAMPLE_KEYS.map((k) => byKey.get(k)).filter(
    Boolean,
  ) as AssetOverview[];

  const count = (type: AssetType) => all.filter((r) => r.type === type).length;
  const view = all.filter((r) => r.type === activeType);

  // Populyar bölmənin başına YALNIZ yuxarı yumşaq scroll (sticky header qədər).
  function scrollToTop(): number | null {
    const el = sectionRef.current;
    if (!el) return null;
    const header = document.querySelector("header");
    const offset = (header?.offsetHeight ?? 64) + 12;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    if (window.scrollY > top + 1) {
      window.scrollTo({ top, behavior: "smooth" });
      return top;
    }
    return null;
  }

  // Aç → dərhal. Bağla → əvvəlcə yumşaq yuxarı scroll (siyahı hələ açıqdır →
  // kəskin atma yox), scroll bitəndən SONRA bağla (assets ilə eyni davranış).
  function toggle() {
    if (!expanded) {
      setExpanded(true);
      return;
    }
    const scrolled = scrollToTop();
    if (scrolled === null) {
      setExpanded(false);
      return;
    }
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      window.removeEventListener("scrollend", finish);
      setExpanded(false);
    };
    window.addEventListener("scrollend", finish);
    window.setTimeout(finish, 900);
  }

  return (
    <section ref={sectionRef} className="mt-10">
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

        {/* Dow Jones-un altında aç/bağla düyməsi */}
        <button
          onClick={toggle}
          aria-expanded={expanded}
          className="flex w-full items-center justify-center gap-2 border-t border-border bg-surface py-2.5 text-xs font-medium text-muted transition-colors hover:bg-surface-hover hover:text-accent"
        >
          {expanded ? t("watch.showLess") : t("watch.showAll")}
          <ChevronDown
            size={15}
            className={`transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {/* yumşaq açılan/bağlanan tam siyahı — max-height + opacity keçidi */}
      <div
        className={`overflow-hidden transition-all ease-out motion-reduce:transition-none ${
          expanded
            ? "mt-4 max-h-[5000px] opacity-100 duration-500"
            : "max-h-0 opacity-0 duration-300"
        }`}
      >
        <div>
          <div className="flex flex-col gap-4 sm:flex-row">
            {/* seçilmiş kateqoriyanın cədvəli — solda */}
            <div className="min-w-0 flex-1 overflow-hidden rounded-card border border-border">
              <table className="w-full text-sm">
                <AssetTableHead />
                <tbody>
                  {all.length === 0
                    ? Array.from({ length: 6 }).map((_, i) => (
                        <SkeletonRow key={i} />
                      ))
                    : view.map((r, i) => (
                        <AssetRow key={r.key} row={r} rank={i + 1} />
                      ))}
                </tbody>
              </table>
            </div>

            {/* kateqoriya seçici — sağda (mobildə yuxarıda) */}
            <nav className="order-first flex gap-2 overflow-x-auto pb-1 sm:order-none sm:w-44 sm:shrink-0 sm:flex-col sm:overflow-visible sm:pb-0">
              {TYPE_ORDER.map((type) => {
                const isActive = type === activeType;
                return (
                  <button
                    key={type}
                    onClick={() => setActiveType(type)}
                    className={`flex shrink-0 items-center justify-between gap-3 rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "border-accent/50 bg-accent-soft text-accent"
                        : "border-border text-muted hover:text-text"
                    }`}
                  >
                    <span>{t(`atype.${type}`)}</span>
                    <span className="font-mono text-xs text-muted">
                      {count(type)}
                    </span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>
    </section>
  );
}
