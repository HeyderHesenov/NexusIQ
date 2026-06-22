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
import type { Asset, AssetDetail, AssetOverview } from "@/types";

/**
 * Kripto sektor xəritəsi (baza simvolu → sektor). Binance top-50 dinamik
 * olduğu üçün yalnız siyahıda olan coinlər görünür; tanınmayan coin sektorsuz.
 */
const CRYPTO_SECTOR: Record<string, "ai" | "perpdex" | "rwa"> = {
  // AI
  TAO: "ai", FET: "ai", RENDER: "ai", RNDR: "ai", WLD: "ai", NEAR: "ai",
  GRT: "ai", VIRTUAL: "ai", IO: "ai", KAITO: "ai", ARKM: "ai",
  AGIX: "ai", OCEAN: "ai", AKT: "ai", AIOZ: "ai", PHA: "ai", AI16Z: "ai",
  // Perp DEX
  HYPE: "perpdex", ASTER: "perpdex", DYDX: "perpdex", GMX: "perpdex",
  JUP: "perpdex", AEVO: "perpdex", GNS: "perpdex", SNX: "perpdex",
  AVNT: "perpdex", DRIFT: "perpdex", APEX: "perpdex", VRTX: "perpdex",
  // RWA (real-world assets)
  ONDO: "rwa", PENDLE: "rwa", OM: "rwa", POLYX: "rwa", CFG: "rwa",
  PLUME: "rwa", RSR: "rwa", USUAL: "rwa", XAUT: "rwa", PAXG: "rwa",
};

const cryptoSector = (r: AssetOverview) => CRYPTO_SECTOR[r.label.toUpperCase()];

type Sub = { key: string; labelKey: string; match: (r: AssetOverview) => boolean };
type Group = { key: string; labelKey: string; subs: Sub[] };

/** İki-səviyyəli kateqoriya ağacı (üst qrup → alt sektorlar). */
const GROUPS: Group[] = [
  {
    key: "crypto",
    labelKey: "atype.crypto",
    subs: [
      { key: "crypto.all", labelKey: "sub.all", match: (r) => r.type === "crypto" },
      { key: "crypto.ai", labelKey: "market.aiCoins", match: (r) => r.type === "crypto" && cryptoSector(r) === "ai" },
      { key: "crypto.perpdex", labelKey: "market.perpDex", match: (r) => r.type === "crypto" && cryptoSector(r) === "perpdex" },
      { key: "crypto.rwa", labelKey: "market.rwa", match: (r) => r.type === "crypto" && cryptoSector(r) === "rwa" },
    ],
  },
  {
    key: "forex",
    labelKey: "atype.forex",
    subs: [
      { key: "forex.fx", labelKey: "market.currencies", match: (r) => r.type === "forex" },
      { key: "forex.metal", labelKey: "market.metals", match: (r) => r.type === "metal" },
    ],
  },
  {
    key: "us",
    labelKey: "navg.us",
    subs: [
      { key: "us.index", labelKey: "atype.index", match: (r) => r.type === "index" },
      { key: "us.ai", labelKey: "market.aiStocks", match: (r) => r.type === "stock" },
    ],
  },
  {
    key: "commodity",
    labelKey: "atype.commodity",
    subs: [
      { key: "commodity.all", labelKey: "sub.all", match: (r) => r.type === "commodity" },
    ],
  },
];

const ALL_SUBS = GROUPS.flatMap((g) => g.subs);

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
  const [activeSub, setActiveSub] = useState("crypto.all");
  const [openGroup, setOpenGroup] = useState("crypto");

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

  const subCount = (s: Sub) => all.filter(s.match).length;
  const groupCount = (g: Group) =>
    all.filter((r) => g.subs.some((s) => s.match(r))).length;
  const activeSubObj = ALL_SUBS.find((s) => s.key === activeSub) ?? ALL_SUBS[0];
  const view = all.filter(activeSubObj.match);

  // Qrup başlığına klik: bağlıdırsa aç + ilk alt-sektoru seç; açıqdırsa bağla.
  function pickGroup(g: Group) {
    if (openGroup === g.key) {
      setOpenGroup("");
      return;
    }
    setOpenGroup(g.key);
    setActiveSub(g.subs[0].key);
  }

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
            {/* seçilmiş alt-sektorun cədvəli — solda */}
            <div className="min-w-0 flex-1 overflow-hidden rounded-card border border-border">
              <table className="w-full text-sm">
                <AssetTableHead />
                <tbody>
                  {all.length === 0 ? (
                    Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)
                  ) : view.length === 0 ? (
                    <tr className="border-t border-border">
                      <td
                        colSpan={6}
                        className="px-3 py-10 text-center text-sm text-muted"
                      >
                        {t("picker.none")}
                      </td>
                    </tr>
                  ) : (
                    view.map((r, i) => <AssetRow key={r.key} row={r} rank={i + 1} />)
                  )}
                </tbody>
              </table>
            </div>

            {/* iki-səviyyəli kateqoriya seçici — sağda (mobildə yuxarıda) */}
            <nav className="order-first flex flex-col gap-1 sm:order-none sm:w-48 sm:shrink-0">
              {GROUPS.map((g) => {
                const open = openGroup === g.key;
                return (
                  <div key={g.key}>
                    <button
                      onClick={() => pickGroup(g)}
                      aria-expanded={open}
                      className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors ${
                        open
                          ? "border-accent/40 bg-accent-soft text-accent"
                          : "border-border text-muted hover:text-text"
                      }`}
                    >
                      <span>{t(g.labelKey)}</span>
                      <span className="flex items-center gap-2">
                        <span className="font-mono text-xs text-muted">
                          {groupCount(g)}
                        </span>
                        <ChevronDown
                          size={14}
                          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
                        />
                      </span>
                    </button>

                    {/* alt-sektorlar — yumşaq açılır, sol bağlayıcı xətt */}
                    <div
                      className={`overflow-hidden transition-all duration-300 ease-out motion-reduce:transition-none ${
                        open ? "max-h-60 opacity-100" : "max-h-0 opacity-0"
                      }`}
                    >
                      <div className="ml-3 mt-1 flex flex-col gap-1 border-l border-border pb-1 pl-3">
                        {g.subs.map((s) => {
                          const active = s.key === activeSub;
                          return (
                            <button
                              key={s.key}
                              onClick={() => setActiveSub(s.key)}
                              className={`flex items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-[13px] transition-colors ${
                                active
                                  ? "bg-accent-soft text-accent"
                                  : "text-muted hover:text-text"
                              }`}
                            >
                              <span>{t(s.labelKey)}</span>
                              <span className="font-mono text-[11px] text-muted">
                                {subCount(s)}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
            </nav>
          </div>
        </div>
      </div>
    </section>
  );
}
