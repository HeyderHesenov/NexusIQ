"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { AssetPicker } from "@/components/assets/AssetPicker";
import { getAssets, getPortfolioIntel } from "@/lib/api";
import {
  addHolding,
  isHeld,
  removeHolding,
  updateHolding,
  useHoldings,
} from "@/lib/holdings";
import { localizedNews } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { Asset, PortfolioIntel, Position } from "@/types";

function fmt(n: number | null | undefined, dp = 0): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}
const signCls = (n: number | null | undefined) =>
  n === null || n === undefined ? "text-muted" : n >= 0 ? "text-up" : "text-down";

export default function PortfolioPage() {
  const { t } = useI18n();
  const holdings = useHoldings();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [data, setData] = useState<PortfolioIntel | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAssets().then(setAssets);
  }, []);

  // Holdings dəyişəndə portfeli təzələ (debounce — hər klaviş vuruşunda yox).
  const sig = holdings.map((h) => `${h.key}:${h.qty}:${h.avgCost}`).join("|");
  const debRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (holdings.length === 0) {
      setData(null);
      return;
    }
    if (debRef.current) clearTimeout(debRef.current);
    setLoading(true);
    debRef.current = setTimeout(() => {
      getPortfolioIntel(
        holdings.map((h) => ({ key: h.key, qty: h.qty, avgCost: h.avgCost })),
        null,
      ).then((d) => {
        setData(d);
        setLoading(false);
      });
    }, 350);
    return () => {
      if (debRef.current) clearTimeout(debRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig]);

  const posByKey = new Map((data?.positions ?? []).map((p) => [p.key, p]));
  const totals = data?.totals;

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="shell flex-1 py-8">
        <div className="mb-6">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
            {t("portfel.eyebrow")}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            {t("portfel.title")}
          </h1>
        </div>

        {/* P&L xülasə hero */}
        {holdings.length > 0 && totals && (
          <section className="mb-6 rounded-card border border-border bg-surface p-5">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-wider text-muted">
                  {t("portfel.totalValue")}
                </p>
                <p className="mt-1 font-mono text-3xl font-semibold tracking-tight text-text">
                  ${fmt(totals.value)}
                </p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[11px] uppercase tracking-wider text-muted">
                  {t("portfel.totalPnl")}
                </p>
                <p className={`mt-1 font-mono text-2xl font-semibold ${signCls(totals.pnl)}`}>
                  {totals.pnl !== null
                    ? `${totals.pnl >= 0 ? "+" : "−"}$${fmt(Math.abs(totals.pnl))}`
                    : "—"}
                  {totals.pnlPct !== null && (
                    <span className="ml-2 text-base">
                      ({totals.pnlPct >= 0 ? "+" : ""}
                      {totals.pnlPct}%)
                    </span>
                  )}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Aktiv əlavə et */}
        <div className="mb-5">
          {assets.length > 0 && (
            <AssetPicker
              assets={assets}
              isSelected={(k) => isHeld(k)}
              onToggle={(k) => (isHeld(k) ? removeHolding(k) : addHolding(k))}
            />
          )}
        </div>

        {holdings.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border py-20 text-center">
            <p className="text-base font-medium text-text">{t("portfel.emptyTitle")}</p>
            <p className="mt-1.5 max-w-sm text-sm text-muted">{t("portfel.emptyHint")}</p>
          </div>
        ) : (
          <>
            {/* Mövqe cədvəli */}
            <section className="mb-8 overflow-hidden rounded-card border border-border bg-surface">
              <div className="hidden grid-cols-[1.4fr_0.9fr_1fr_0.9fr_1.1fr_1fr_0.3fr] gap-3 border-b border-border px-4 py-2.5 font-mono text-[10px] uppercase tracking-wider text-muted md:grid">
                <span>{t("portfel.colAsset")}</span>
                <span className="text-right">{t("portfel.colQty")}</span>
                <span className="text-right">{t("portfel.colCost")}</span>
                <span className="text-right">{t("portfel.colPrice")}</span>
                <span>{t("portfel.colWeight")}</span>
                <span className="text-right">{t("portfel.colPnl")}</span>
                <span />
              </div>
              {holdings.map((h) => (
                <PositionRow
                  key={h.key}
                  hkey={h.key}
                  qty={h.qty}
                  avgCost={h.avgCost}
                  pos={posByKey.get(h.key)}
                  t={t}
                />
              ))}
            </section>

            {/* Puluna ən çox təsir edən xəbərlər */}
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold tracking-tight">
                {t("portfel.newsTitle")}
              </h2>
              {loading && (
                <span className="font-mono text-[10px] text-muted">
                  {t("portfel.updating")}
                </span>
              )}
            </div>
            {data && data.news.length > 0 ? (
              <div className="grid grid-cols-1 gap-2.5">
                {data.news.slice(0, 12).map((n) => (
                  <MoneyNewsRow key={n.id} n={n} posByKey={posByKey} t={t} />
                ))}
              </div>
            ) : (
              <p className="rounded-card border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
                {t("portfel.noNews")}
              </p>
            )}
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}

function PositionRow({
  hkey,
  qty,
  avgCost,
  pos,
  t,
}: {
  hkey: string;
  qty: number;
  avgCost: number;
  pos: Position | undefined;
  t: (k: string) => string;
}) {
  return (
    <div className="grid grid-cols-2 items-center gap-3 border-b border-border px-4 py-3 last:border-b-0 md:grid-cols-[1.4fr_0.9fr_1fr_0.9fr_1.1fr_1fr_0.3fr]">
      <div className="col-span-2 flex items-center gap-2 md:col-span-1">
        <span className="font-mono text-sm font-semibold text-text">
          {pos?.label ?? hkey.toUpperCase()}
        </span>
        {pos?.chgPct !== null && pos?.chgPct !== undefined && (
          <span className={`font-mono text-[11px] ${signCls(pos.chgPct)}`}>
            {pos.chgPct >= 0 ? "+" : ""}
            {pos.chgPct}%
          </span>
        )}
      </div>

      <label className="flex items-center justify-between gap-1 md:justify-end">
        <span className="font-mono text-[10px] uppercase text-muted md:hidden">
          {t("portfel.colQty")}
        </span>
        <input
          type="number"
          inputMode="decimal"
          defaultValue={qty}
          min={0}
          step="any"
          onChange={(e) =>
            updateHolding(hkey, { qty: Math.max(0, Number(e.target.value) || 0) })
          }
          className="w-24 rounded-md border border-border bg-bg px-2 py-1 text-right font-mono text-sm text-text focus:border-accent focus:outline-none"
        />
      </label>

      <label className="flex items-center justify-between gap-1 md:justify-end">
        <span className="font-mono text-[10px] uppercase text-muted md:hidden">
          {t("portfel.colCost")}
        </span>
        <input
          type="number"
          inputMode="decimal"
          defaultValue={avgCost || ""}
          min={0}
          step="any"
          placeholder="0"
          onChange={(e) =>
            updateHolding(hkey, { avgCost: Math.max(0, Number(e.target.value) || 0) })
          }
          className="w-24 rounded-md border border-border bg-bg px-2 py-1 text-right font-mono text-sm text-text focus:border-accent focus:outline-none"
        />
      </label>

      <span className="hidden text-right font-mono text-sm text-text md:block">
        {pos?.price !== null && pos?.price !== undefined ? fmt(pos.price, 2) : "—"}
      </span>

      <div className="hidden items-center gap-2 md:flex">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-hover">
          <div
            className="h-full rounded-full bg-accent"
            style={{ width: `${Math.round((pos?.weight ?? 0) * 100)}%` }}
          />
        </div>
        <span className="w-9 shrink-0 text-right font-mono text-[11px] text-muted">
          {Math.round((pos?.weight ?? 0) * 100)}%
        </span>
      </div>

      <div className="col-span-2 text-right md:col-span-1">
        <span className={`font-mono text-sm font-semibold ${signCls(pos?.pnl)}`}>
          {pos?.pnl !== null && pos?.pnl !== undefined
            ? `${pos.pnl >= 0 ? "+" : "−"}$${fmt(Math.abs(pos.pnl))}`
            : "—"}
        </span>
        {pos?.pnlPct !== null && pos?.pnlPct !== undefined && (
          <span className={`ml-1.5 font-mono text-[11px] ${signCls(pos.pnlPct)}`}>
            ({pos.pnlPct >= 0 ? "+" : ""}
            {pos.pnlPct}%)
          </span>
        )}
      </div>

      <button
        onClick={() => removeHolding(hkey)}
        aria-label={t("portfel.remove")}
        className="justify-self-end text-muted transition-colors hover:text-down"
      >
        <Trash2 size={15} />
      </button>
    </div>
  );
}

function MoneyNewsRow({
  n,
  posByKey,
  t,
}: {
  n: import("@/types").PortfolioNews;
  posByKey: Map<string, Position>;
  t: (k: string) => string;
}) {
  const { lang } = useI18n();
  const { title } = localizedNews(n, lang);
  const tilt = n.moneyTilt ?? 0;
  const tiltCls = tilt > 0.001 ? "text-up" : tilt < -0.001 ? "text-down" : "text-muted";
  const rel = Math.min(100, Math.round((n.relevanceScore ?? 0) * 100));

  return (
    <Link
      href={`/news/${n.id}`}
      className="group flex items-center gap-3 rounded-card border border-border bg-surface px-4 py-3 transition-colors hover:border-accent/50"
    >
      {/* təsir bar (pul-çəkili relevance) */}
      <div className="flex w-14 shrink-0 flex-col items-center gap-1" title={t("portfel.relevance")}>
        <div className="flex h-8 w-1.5 items-end overflow-hidden rounded-full bg-surface-hover">
          <div
            className={`w-full rounded-full ${tilt >= 0 ? "bg-up" : "bg-down"}`}
            style={{ height: `${Math.max(8, rel)}%` }}
          />
        </div>
        <span className={`font-mono text-[10px] ${tiltCls}`}>
          {tilt >= 0 ? "▲" : "▼"}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-medium leading-snug text-text">
          {title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {(n.touched ?? []).map((k) => (
            <span
              key={k}
              className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted"
            >
              {posByKey.get(k)?.label ?? k.toUpperCase()}
            </span>
          ))}
          <span className="truncate text-[11px] text-muted">{n.source ?? ""}</span>
        </div>
      </div>
    </Link>
  );
}
