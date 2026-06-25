"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Calendar, ChevronDown, Search, SlidersHorizontal } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { useClickOutside } from "@/lib/useClickOutside";
import { briefHref } from "@/lib/brief";
import { SaveEventButton } from "@/components/market/SaveEventButton";
import type { CalKind } from "@/lib/marketCategories";
import type {
  CalEvent,
  CryptoUnlock,
  Earning,
  MajorEvent,
  SavedEvent,
} from "@/types";

type SavedPayload = Omit<SavedEvent, "savedAt">;
type RangeKey = "today" | "week" | "nextWeek" | "month" | "custom";

/* ---------- tarix köməkçiləri (gün-açarı: YYYY-MM-DD, leksik müqayisə) ---------- */

const pad = (n: number) => String(n).padStart(2, "0");
const keyOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const addDays = (d: Date, n: number) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};

/* az Intl locale tam dəstəklənmir → lokallaşdırılmış adlar əl ilə (0 = Bazar = JS getDay). */
const WEEKDAYS: Record<string, string[]> = {
  az: ["Bazar", "Bazar ertəsi", "Çərşənbə axşamı", "Çərşənbə", "Cümə axşamı", "Cümə", "Şənbə"],
  en: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  ru: ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"],
  tr: ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"],
};
const MONTHS: Record<string, string[]> = {
  az: ["Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun", "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"],
  en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
  ru: ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
  tr: ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
};

/** "YYYY-MM-DD" → lokallaşdırılmış "Həftəgünü, D Ay". */
function dayLabel(dk: string, lang: string): string {
  const [y, m, d] = dk.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const wd = (WEEKDAYS[lang] ?? WEEKDAYS.en)[date.getDay()];
  const mo = (MONTHS[lang] ?? MONTHS.en)[m - 1];
  return `${wd}, ${d} ${mo}`;
}

/** Elementin gün-açarını (YYYY-MM-DD) qaytarır — events MM-DD-YYYY, qalanı ISO. */
function dayKey(kind: CalKind, item: Record<string, unknown>): string {
  const d = String(item.date ?? "");
  if (kind === "events") {
    const [m, day, y] = d.split("-");
    return y && m && day ? `${y}-${m}-${day}` : d;
  }
  return d; // YYYY-MM-DD
}

/** Preset/xüsusi aralığı [fromKey, toKey] (YYYY-MM-DD, daxiletmə) sərhədlərinə çevirir. */
function rangeBounds(rk: RangeKey, from: string, to: string): [string, string] {
  const today = new Date();
  const tk = keyOf(today);
  const wd = (today.getDay() + 6) % 7; // 0 = Bazar ertəsi
  switch (rk) {
    case "today":
      return [tk, tk];
    case "week":
      return [tk, keyOf(addDays(today, 6 - wd))];
    case "nextWeek": {
      const start = addDays(today, 7 - wd);
      return [keyOf(start), keyOf(addDays(start, 6))];
    }
    case "month":
      return [tk, keyOf(addDays(today, 31))];
    case "custom":
      return [from || tk, to || keyOf(addDays(today, 31))];
  }
}

/* ---------- axtarış mətni + /brief link ---------- */

function itemText(kind: CalKind, it: Record<string, unknown>): string {
  if (kind === "earnings") return `${it.sym} ${it.name}`;
  if (kind === "events") return `${it.title} ${it.country}`;
  return `${it.sym ?? ""} ${it.category ?? ""} ${it.note ?? ""}`;
}

/* ---------- impact göstəricisi (gücü zolaqla) ---------- */

function ImpactBars({ impact }: { impact: string }) {
  const high = impact === "High";
  const color = high ? "bg-down" : "bg-amber-400";
  return (
    <span className="flex items-end gap-[2px]" title={impact}>
      <span className={`h-2 w-[3px] rounded-sm ${color}`} />
      <span className={`h-3 w-[3px] rounded-sm ${high ? color : "bg-border"}`} />
    </span>
  );
}

/* ---------- gün başlığı ---------- */

function DayHeader({
  dk,
  count,
  isToday,
  lang,
  t,
}: {
  dk: string;
  count: number;
  isToday: boolean;
  lang: string;
  t: (k: string) => string;
}) {
  const label = dayLabel(dk, lang);

  return (
    <div className="sticky top-0 z-10 -mx-px flex items-center justify-between border-y border-border bg-surface/92 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="flex items-center gap-2">
        <span
          className={`text-sm font-semibold tracking-tight ${
            isToday ? "text-accent" : "text-text"
          }`}
        >
          {label}
        </span>
        {isToday && (
          <span className="rounded-full bg-accent-soft px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider text-accent">
            {t("market.today")}
          </span>
        )}
      </div>
      <span className="font-mono text-[11px] text-muted">
        {t("market.eventsCount").replace("{n}", String(count))}
      </span>
    </div>
  );
}

/* ---------- sətir (növ üzrə) ---------- */

const ROW =
  "group relative grid items-center gap-x-3 gap-y-1 border-b border-border/60 px-4 py-2.5 transition-colors duration-150 hover:bg-surface-hover";

function Row({
  kind,
  item,
  t,
}: {
  kind: CalKind;
  item: Record<string, unknown>;
  t: (k: string) => string;
}) {
  let href = "#";
  let saved: SavedPayload | null = null;
  let body: React.ReactNode = null;

  if (kind === "events") {
    const e = item as unknown as CalEvent;
    const sub = `${e.country} · ${e.impact} · ${e.time}`;
    href = briefHref({
      kind: "event",
      name: e.title,
      badge: e.country,
      sub,
      meta: `${e.country}, impact ${e.impact}`,
      forecast: e.forecast,
      previous: e.previous,
    });
    saved = {
      id: `event:${e.country}:${e.date}:${e.time}:${e.title}`,
      name: e.title,
      badge: e.country,
      sub,
      href,
    };
    body = (
      <div className="grid grid-cols-[52px_44px_16px_1fr] items-center gap-3 sm:grid-cols-[58px_46px_18px_1fr_minmax(0,2fr)]">
        <span className="font-mono text-[11px] tabular-nums text-muted">{e.time}</span>
        <span className="w-fit rounded bg-surface-hover px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-text/80">
          {e.country}
        </span>
        <ImpactBars impact={e.impact} />
        <p className="truncate text-[13px] font-medium text-text/90">{e.title}</p>
        <div className="col-span-full mt-0.5 flex gap-4 font-mono text-[11px] sm:col-span-1 sm:mt-0 sm:justify-end">
          <Stat label={t("market.actual")} value={e.actual} strong />
          <Stat label={t("market.fc")} value={e.forecast} />
          <Stat label={t("market.prev")} value={e.previous} />
        </div>
      </div>
    );
  } else if (kind === "earnings") {
    const e = item as unknown as Earning;
    const sub = `${e.time}`;
    href = briefHref({ kind: "earnings", name: e.name, sym: e.sym, badge: e.sym, sub, meta: e.date });
    saved = { id: `earn:${e.sym}:${e.date}`, name: e.name, badge: e.sym, sub, href };
    body = (
      <div className="grid grid-cols-[56px_64px_1fr] items-center gap-3">
        <span className="font-mono text-[11px] tabular-nums text-muted">{e.time}</span>
        <span className="w-fit rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
          {e.sym}
        </span>
        <p className="truncate text-[13px] font-medium text-text/90">{e.name}</p>
      </div>
    );
  } else if (kind === "unlocks") {
    const u = item as unknown as CryptoUnlock;
    const sub = `${u.tokens} ${t("market.unlock")}`;
    href = briefHref({
      kind: "unlock",
      name: u.sym,
      sym: u.sym,
      badge: u.sym,
      sub,
      meta: `${u.tokens} tokens, ${u.category}`,
    });
    saved = { id: `unlock:${u.sym}:${u.date}`, name: u.sym, badge: u.sym, sub, href };
    body = (
      <div className="grid grid-cols-[64px_1fr_auto] items-center gap-3">
        <span className="w-fit rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
          {u.sym}
        </span>
        <span className="truncate font-mono text-[11px] uppercase tracking-wider text-muted/80">
          {u.category}
        </span>
        <span className="font-mono text-sm font-semibold tabular-nums text-text/90">
          {u.tokens}{" "}
          <span className="text-[11px] font-normal text-muted">{t("market.unlock")}</span>
        </span>
      </div>
    );
  } else {
    // cryptoEvents
    const e = item as unknown as MajorEvent;
    const name = `${e.sym} — ${t(`market.ev.${e.type}`)}`;
    const sub = t(`market.ev.${e.type}`);
    href = briefHref({
      kind: "cryptoEvent",
      name,
      sym: e.sym,
      badge: e.sym,
      sub,
      meta: `${e.type}, ${e.note}`,
    });
    saved = { id: `cevent:${e.sym}:${e.date}:${e.type}`, name, badge: e.sym, sub, href };
    body = (
      <div className="grid grid-cols-[64px_auto_1fr] items-center gap-3">
        <span className="w-fit rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
          {e.sym}
        </span>
        <span className="text-[13px] font-medium text-text/90">{t(`market.ev.${e.type}`)}</span>
        {e.note && <span className="truncate font-mono text-[11px] text-muted">{e.note}</span>}
      </div>
    );
  }

  return (
    <Link href={href} className={ROW}>
      {body}
      {saved && (
        <div className="absolute right-2 top-2 opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
          <SaveEventButton event={saved} />
        </div>
      )}
    </Link>
  );
}

function Stat({ label, value, strong }: { label: string; value?: string; strong?: boolean }) {
  if (!value) return null;
  return (
    <span className="whitespace-nowrap text-muted">
      {label}:{" "}
      <span className={strong ? "font-semibold text-text" : "text-text/80"}>{value}</span>
    </span>
  );
}

/* ---------- əsas komponent ---------- */

export function CalendarLedger({
  kind,
  items,
  withRange = false,
  withImpact = false,
}: {
  kind: CalKind;
  items: unknown[];
  withRange?: boolean;
  withImpact?: boolean;
}) {
  const { t, lang } = useI18n();
  const [range, setRange] = useState<RangeKey>("week");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [impact, setImpact] = useState<"all" | "High" | "Medium">("all");
  const [query, setQuery] = useState("");
  const [openRange, setOpenRange] = useState(false);
  const rangeRef = useRef<HTMLDivElement>(null);
  useClickOutside(rangeRef, () => setOpenRange(false));

  const todayKey = keyOf(new Date());
  const minKey = todayKey;
  const maxKey = keyOf(addDays(new Date(), 31));

  const groups = useMemo(() => {
    const rows = (items as Record<string, unknown>[]) ?? [];
    const [from, to] = withRange ? rangeBounds(range, customFrom, customTo) : ["", ""];
    const q = query.trim().toLowerCase();

    const map = new Map<string, Record<string, unknown>[]>();
    for (const it of rows) {
      if (withImpact && impact !== "all" && it.impact !== impact) continue;
      if (q && !itemText(kind, it).toLowerCase().includes(q)) continue;
      const dk = dayKey(kind, it);
      if (withRange && (dk < from || dk > to)) continue;
      const bucket = map.get(dk);
      if (bucket) bucket.push(it);
      else map.set(dk, [it]);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [items, kind, range, customFrom, customTo, impact, query, withRange, withImpact]);

  const RANGE_KEYS: RangeKey[] = ["today", "week", "nextWeek", "month"];

  return (
    <section className="overflow-hidden rounded-card border border-border bg-surface">
      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2.5">
        {withRange && (
          <>
            <div className="flex items-center gap-1 rounded-lg border border-border bg-bg/40 p-0.5">
              {RANGE_KEYS.map((rk) => (
                <button
                  key={rk}
                  onClick={() => setRange(rk)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
                    range === rk
                      ? "bg-accent text-white"
                      : "text-muted hover:text-text"
                  }`}
                >
                  {t(`market.range.${rk}`)}
                </button>
              ))}
            </div>

            {/* xüsusi aralıq */}
            <div ref={rangeRef} className="relative">
              <button
                onClick={() => setOpenRange((v) => !v)}
                className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors duration-150 ${
                  range === "custom"
                    ? "border-accent text-accent"
                    : "border-border text-muted hover:text-text"
                }`}
              >
                <Calendar size={13} />
                {t("market.range.custom")}
                <ChevronDown
                  size={12}
                  className={`transition-transform duration-200 ${openRange ? "rotate-180" : ""}`}
                />
              </button>
              {openRange && (
                <div className="absolute left-0 z-30 mt-2 w-60 rounded-xl border border-border bg-surface p-3 shadow-2xl fade-up">
                  <label className="mb-2 block">
                    <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted">
                      {t("market.range.from")}
                    </span>
                    <input
                      type="date"
                      min={minKey}
                      max={maxKey}
                      value={customFrom}
                      onChange={(e) => setCustomFrom(e.target.value)}
                      className="w-full rounded-lg border border-border bg-bg/40 px-2.5 py-1.5 text-sm text-text focus:border-accent focus:outline-none"
                    />
                  </label>
                  <label className="mb-3 block">
                    <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted">
                      {t("market.range.to")}
                    </span>
                    <input
                      type="date"
                      min={customFrom || minKey}
                      max={maxKey}
                      value={customTo}
                      onChange={(e) => setCustomTo(e.target.value)}
                      className="w-full rounded-lg border border-border bg-bg/40 px-2.5 py-1.5 text-sm text-text focus:border-accent focus:outline-none"
                    />
                  </label>
                  <button
                    onClick={() => {
                      setRange("custom");
                      setOpenRange(false);
                    }}
                    disabled={!customFrom || !customTo}
                    className="w-full rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-40"
                  >
                    {t("market.range.apply")}
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {/* impact filtri */}
        {withImpact && (
          <div className="flex items-center gap-1 rounded-lg border border-border bg-bg/40 p-0.5">
            <SlidersHorizontal size={13} className="ml-1.5 text-muted" />
            {(["all", "High", "Medium"] as const).map((im) => (
              <button
                key={im}
                onClick={() => setImpact(im)}
                className={`rounded-md px-2 py-1 text-xs font-medium transition-colors duration-150 ${
                  impact === im ? "bg-surface-hover text-text" : "text-muted hover:text-text"
                }`}
              >
                {im === "all"
                  ? t("market.allImpact")
                  : t(`market.impact.${im.toLowerCase()}`)}
              </button>
            ))}
          </div>
        )}

        {/* axtarış */}
        <div className="ml-auto flex min-w-[140px] flex-1 items-center gap-2 rounded-lg border border-border bg-bg/40 px-2.5 py-1.5 sm:max-w-[220px] sm:flex-none">
          <Search size={13} className="text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("market.searchPh").replace("{x}", kind === "events" ? "CPI" : "")}
            className="w-full bg-transparent text-sm text-text placeholder:text-muted/60 focus:outline-none"
          />
        </div>
      </div>

      {/* siyahı */}
      {groups.length === 0 ? (
        <p className="px-4 py-10 text-center text-sm text-muted">{t("market.calEmpty")}</p>
      ) : (
        <div className="max-h-[70vh] overflow-y-auto">
          {groups.map(([dk, rows]) => (
            <div key={dk}>
              <DayHeader
                dk={dk}
                count={rows.length}
                isToday={dk === todayKey}
                lang={lang}
                t={t}
              />
              {rows.map((it, i) => (
                <Row key={i} kind={kind} item={it} t={t} />
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
