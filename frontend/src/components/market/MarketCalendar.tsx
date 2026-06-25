"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { CalendarDays, Check, ChevronDown, Search } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { useClickOutside } from "@/lib/useClickOutside";
import { CalendarLedger } from "@/components/market/CalendarLedger";
import type { CalCategory } from "@/lib/marketCategories";
import type { Quote } from "@/types";

/** Kiçik trend qrafiki — son qiymətlərdən SVG polyline. */
function Sparkline({ data }: { data: number[] }) {
  if (!data || data.length < 2) return null;
  const w = 72;
  const h = 22;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const up = data[data.length - 1] >= data[0];
  return (
    <svg width={w} height={h} className="mt-0.5 overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke={up ? "#34d399" : "#f43f5e"}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function briefHref(params: Record<string, string>): string {
  return "/brief?" + new URLSearchParams(params).toString();
}

/** Canlı qiymət kartı (metallar / əmtəələr) — tarixsiz, grid-də. */
function PriceCard({ q }: { q: Quote }) {
  return (
    <Link
      href={briefHref({
        kind: "asset",
        name: q.sym,
        sym: q.sym,
        badge: q.sym,
        sub: `${q.val}  ${q.chg}`,
      })}
      className="flex flex-col gap-1.5 rounded-xl border border-border bg-bg/40 px-3.5 py-3 transition-colors duration-150 hover:border-accent/60"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] font-semibold tracking-wider text-text/80">
          {q.sym}
        </span>
        <span className={`font-mono text-[12px] ${q.up ? "text-emerald-400" : "text-rose-400"}`}>
          {q.chg}
        </span>
      </div>
      <span className="font-mono text-lg font-semibold tabular-nums text-text">{q.val}</span>
      {q.spark && <Sparkline data={q.spark} />}
    </Link>
  );
}

export function MarketCalendar({ categories }: { categories: CalCategory[] }) {
  const { t } = useI18n();
  const [idx, setIdx] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<unknown[] | null>(null);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIdx(0);
  }, [categories]);

  const active = categories[idx] ?? categories[0];

  useEffect(() => {
    let alive = true;
    setItems(null);
    setQuery("");
    active.load().then((d) => alive && setItems(d));
    return () => {
      alive = false;
    };
  }, [active]);

  useClickOutside(ref, () => setOpen(false));

  const isPrices = active.kind === "prices";
  const prices = (items as Quote[] | null) ?? null;
  const q = query.trim().toLowerCase();
  const shownPrices =
    prices && q
      ? prices.filter((p) => p.sym.toLowerCase().includes(q))
      : prices;

  return (
    <section>
      {/* başlıq + kateqoriya seçici */}
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <CalendarDays size={14} className="text-accent" />
          <span className="font-mono text-xs uppercase tracking-[0.15em] text-accent">
            {t("market.calTitle")}
          </span>
        </div>

        <div ref={ref} className="relative">
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface/80 px-3 py-1.5 text-sm text-text transition-all duration-200 hover:border-accent"
          >
            <span className="font-medium">{t(active.labelKey)}</span>
            <ChevronDown
              size={14}
              className={`text-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            />
          </button>

          {open && (
            <div className="absolute right-0 z-50 mt-2 w-48 overflow-hidden rounded-xl border border-border bg-surface shadow-2xl fade-up">
              {categories.map((c, i) => (
                <button
                  key={c.key}
                  onClick={() => {
                    setIdx(i);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center justify-between px-3.5 py-2.5 text-sm transition-colors duration-150 hover:bg-surface-hover ${
                    i === idx ? "text-accent" : "text-text"
                  }`}
                >
                  {t(c.labelKey)}
                  {i === idx && <Check size={15} />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* yüklənir */}
      {!items && (
        <div className="rounded-card border border-border bg-surface p-4">
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-11 w-full animate-pulse rounded-lg border border-border bg-surface-hover"
              />
            ))}
          </div>
        </div>
      )}

      {/* canlı qiymətlər — grid */}
      {items && isPrices && (
        <div className="rounded-card border border-border bg-surface p-4">
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-border bg-bg/40 px-3 py-2">
            <Search size={14} className="text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("market.searchPh").replace("{x}", active.searchEx ?? "")}
              className="w-full bg-transparent text-sm text-text placeholder:text-muted/60 focus:outline-none"
            />
          </div>
          {shownPrices && shownPrices.length > 0 ? (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
              {shownPrices.map((p, i) => (
                <PriceCard key={i} q={p} />
              ))}
            </div>
          ) : (
            <p className="px-3.5 py-8 text-center text-sm text-muted">{t("market.calEmpty")}</p>
          )}
        </div>
      )}

      {/* tarix-əsaslı — ForexFactory cədvəli */}
      {items && !isPrices && (
        <CalendarLedger
          kind={active.kind}
          items={items}
          withRange={active.kind === "events"}
          withImpact={active.kind === "events"}
        />
      )}
    </section>
  );
}
