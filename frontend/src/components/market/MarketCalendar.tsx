"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { CalendarDays, Check, ChevronDown, Search } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { useClickOutside } from "@/lib/useClickOutside";
import { SaveEventButton } from "@/components/market/SaveEventButton";
import type { CalCategory, CalKind } from "@/lib/marketCategories";
import type {
  CalEvent,
  CryptoUnlock,
  Earning,
  MajorEvent,
  Quote,
  SavedEvent,
} from "@/types";

type SavedPayload = Omit<SavedEvent, "savedAt">;

/** Kart + (təqvim hadisəsidirsə) hover-də görünən saxla düyməsi. */
function SaveWrap({
  saved,
  children,
}: {
  saved: SavedPayload | null;
  children: React.ReactNode;
}) {
  return (
    <div className="group relative shrink-0">
      {children}
      {saved && (
        <div className="absolute bottom-1.5 right-1.5 opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
          <SaveEventButton event={saved} />
        </div>
      )}
    </div>
  );
}

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

/** "YYYY-MM-DD" → "DD.MM". */
const fromISO = (d: string) => {
  const [, m, day] = d.split("-");
  return m && day ? `${day}.${m}` : d;
};
/** "MM-DD-YYYY" → "DD.MM". */
const fromUS = (d: string) => {
  const [m, day] = d.split("-");
  return m && day ? `${day}.${m}` : d;
};

const RAIL =
  "flex gap-2.5 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden";
const CARD =
  "flex shrink-0 flex-col gap-1.5 rounded-xl border border-border bg-bg/40 px-3.5 py-3 transition-colors duration-150 hover:border-accent/60";

/** /brief səhifəsinə link qurur. */
function briefHref(params: Record<string, string>): string {
  return "/brief?" + new URLSearchParams(params).toString();
}

/** Element üzərində axtarış üçün mətn (növ üzrə). */
function itemText(kind: CalKind, it: unknown): string {
  const o = it as Record<string, unknown>;
  if (kind === "earnings") return `${o.sym} ${o.name}`;
  if (kind === "events") return `${o.title} ${o.country}`;
  return `${o.sym ?? ""}`;
}

export function MarketCalendar({ categories }: { categories: CalCategory[] }) {
  const { t } = useI18n();
  const [idx, setIdx] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<unknown[] | null>(null);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  // tab dəyişəndə ilk kateqoriyaya qayıt
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

  const q = query.trim().toLowerCase();
  const shown =
    items && q
      ? items.filter((it) => itemText(active.kind, it).toLowerCase().includes(q))
      : items;

  useClickOutside(ref, () => setOpen(false));

  return (
    <section className="mb-6 rounded-card border border-border bg-surface px-5 py-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <CalendarDays size={14} className="text-accent" />
          <span className="font-mono text-xs uppercase tracking-[0.15em] text-accent">
            {t("market.calTitle")}
          </span>
        </div>

        {/* kateqoriya seçici — dil seçici stilində */}
        <div ref={ref} className="relative">
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface/80 px-3 py-1.5 text-sm text-text transition-all duration-200 hover:border-accent"
          >
            <span className="font-medium">{t(active.labelKey)}</span>
            <ChevronDown
              size={14}
              className={`text-muted transition-transform duration-200 ${
                open ? "rotate-180" : ""
              }`}
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

      {/* axtarış qutusu — çoxlu elementli kateqoriyalarda */}
      {active.searchable && items && items.length > 0 && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-border bg-bg/40 px-3 py-2">
          <Search size={14} className="text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("market.searchPh").replace("{x}", active.searchEx ?? "")}
            className="w-full bg-transparent text-sm text-text placeholder:text-muted/60 focus:outline-none"
          />
        </div>
      )}

      {/* yüklənir */}
      {!items && (
        <div className={RAIL}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-[64px] w-44 shrink-0 animate-pulse rounded-xl border border-border bg-surface-hover"
            />
          ))}
        </div>
      )}

      {/* boş */}
      {shown && shown.length === 0 && (
        <p className="rounded-lg border border-dashed border-border px-3.5 py-4 text-center text-xs text-muted">
          {t("market.calEmpty")}
        </p>
      )}

      {/* məzmun */}
      {shown && shown.length > 0 && (
        <div className={RAIL}>
          {shown.map((it, i) => (
            <Card key={i} kind={active.kind} item={it} t={t} />
          ))}
        </div>
      )}
    </section>
  );
}

function Card({
  kind,
  item,
  t,
}: {
  kind: CalKind;
  item: unknown;
  t: (k: string) => string;
}) {
  if (kind === "earnings") {
    const e = item as Earning;
    const sub = `${fromISO(e.date)} · ${e.time}`;
    const href = briefHref({
      kind: "earnings",
      name: e.name,
      sym: e.sym,
      badge: e.sym,
      sub,
      meta: e.date,
    });
    return (
      <SaveWrap
        saved={{ id: `earn:${e.sym}:${e.date}`, name: e.name, badge: e.sym, sub, href }}
      >
        <Link href={href} className={`${CARD} w-44`}>
          <div className="flex items-center justify-between">
            <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
              {e.sym}
            </span>
            <span className="font-mono text-[11px] text-muted">
              {fromISO(e.date)} · {e.time}
            </span>
          </div>
          <span className="truncate text-[13px] font-medium text-text/90">{e.name}</span>
        </Link>
      </SaveWrap>
    );
  }

  if (kind === "unlocks") {
    const u = item as CryptoUnlock;
    const sub = `${fromISO(u.date)} · ${u.tokens} ${t("market.unlock")}`;
    const href = briefHref({
      kind: "unlock",
      name: u.sym,
      sym: u.sym,
      badge: u.sym,
      sub,
      meta: `${u.tokens} tokens, ${u.category}`,
    });
    return (
      <SaveWrap
        saved={{ id: `unlock:${u.sym}:${u.date}`, name: u.sym, badge: u.sym, sub, href }}
      >
        <Link href={href} className={`${CARD} w-44`}>
          <div className="flex items-center justify-between">
            <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
              {u.sym}
            </span>
            <span className="font-mono text-[11px] text-muted">{fromISO(u.date)}</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-sm font-semibold tabular-nums text-text/90">
              {u.tokens}
            </span>
            <span className="text-[11px] text-muted">{t("market.unlock")}</span>
          </div>
          {u.category && (
            <span className="truncate font-mono text-[10px] uppercase tracking-wider text-muted/70">
              {u.category}
            </span>
          )}
        </Link>
      </SaveWrap>
    );
  }

  if (kind === "prices") {
    // canlı qiymət — təqvim hadisəsi deyil, saxlanmır.
    const q = item as Quote;
    return (
      <SaveWrap saved={null}>
        <Link
          href={briefHref({
            kind: "asset",
            name: q.sym,
            sym: q.sym,
            badge: q.sym,
            sub: `${q.val}  ${q.chg}`,
          })}
          className={`${CARD} w-44`}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] font-semibold tracking-wider text-text/80">
              {q.sym}
            </span>
            <span
              className={`font-mono text-[12px] ${q.up ? "text-emerald-400" : "text-rose-400"}`}
            >
              {q.chg}
            </span>
          </div>
          <span className="font-mono text-lg font-semibold tabular-nums text-text">
            {q.val}
          </span>
          {q.spark && <Sparkline data={q.spark} />}
        </Link>
      </SaveWrap>
    );
  }

  if (kind === "cryptoEvents") {
    const e = item as MajorEvent;
    const name = `${e.sym} — ${t(`market.ev.${e.type}`)}`;
    const sub = `${t(`market.ev.${e.type}`)} · ${fromISO(e.date)}`;
    const href = briefHref({
      kind: "cryptoEvent",
      name,
      sym: e.sym,
      badge: e.sym,
      sub,
      meta: `${e.type}, ${e.note}`,
    });
    return (
      <SaveWrap
        saved={{ id: `cevent:${e.sym}:${e.date}:${e.type}`, name, badge: e.sym, sub, href }}
      >
        <Link href={href} className={`${CARD} w-44`}>
          <div className="flex items-center justify-between">
            <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
              {e.sym}
            </span>
            <span className="font-mono text-[11px] text-muted">{fromISO(e.date)}</span>
          </div>
          <span className="text-[13px] font-medium text-text/90">
            {t(`market.ev.${e.type}`)}
          </span>
          {e.note && (
            <span className="font-mono text-[11px] text-muted">{e.note}</span>
          )}
        </Link>
      </SaveWrap>
    );
  }

  // events — klikləndə hadisə analiz səhifəsi açılır (yeni tab)
  const e = item as CalEvent;
  const sub = `${e.country} · ${e.impact} · ${fromUS(e.date)} ${e.time}`;
  const href = briefHref({
    kind: "event",
    name: e.title,
    badge: e.country,
    sub,
    meta: `${e.country}, impact ${e.impact}`,
    forecast: e.forecast,
    previous: e.previous,
  });
  return (
    <SaveWrap
      saved={{
        id: `event:${e.country}:${e.date}:${e.time}:${e.title}`,
        name: e.title,
        badge: e.country,
        sub,
        href,
      }}
    >
      <Link href={href} className={`${CARD} w-48`}>
        <div className="flex items-center justify-between">
          <span className="rounded bg-surface-hover px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-text/80">
            {e.country}
          </span>
          <span className="flex items-center gap-1.5 font-mono text-[11px] text-muted">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                e.impact === "High" ? "bg-rose-400" : "bg-amber-400"
              }`}
            />
            {fromUS(e.date)} · {e.time}
          </span>
        </div>
        <p className="line-clamp-2 text-[13px] font-medium leading-snug text-text/90">
          {e.title}
        </p>
        {(e.forecast || e.previous) && (
          <div className="flex gap-3 font-mono text-[11px] text-muted">
            {e.forecast && (
              <span>
                {t("market.fc")}: <span className="text-text/80">{e.forecast}</span>
              </span>
            )}
            {e.previous && (
              <span>
                {t("market.prev")}: <span className="text-text/80">{e.previous}</span>
              </span>
            )}
          </div>
        )}
      </Link>
    </SaveWrap>
  );
}
