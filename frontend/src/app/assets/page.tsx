"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Search, Coins, ChevronDown } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import {
  AssetRow,
  AssetTableHead,
  SkeletonRow,
} from "@/components/assets/AssetTable";
import { getAssetsOverview } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssetOverview, AssetType } from "@/types";

const FILTERS: AssetType[] = ["crypto", "index", "forex", "metal", "commodity"];

export default function AssetsPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState<AssetOverview[]>([]);
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [filter, setFilter] = useState<AssetType>("crypto");
  const [q, setQ] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [collapsing, setCollapsing] = useState(false);
  const tableRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    getAssetsOverview().then((d) => {
      setRows(d);
      setStatus("ready");
    });
  }, []);

  // filtr və ya axtarış dəyişəndə yenidən ilk 10-a qayıt
  useEffect(() => {
    setShowAll(false);
    setCollapsing(false);
  }, [filter, q]);

  // Açıq rAF-i unmount-da təmizlə.
  useEffect(
    () => () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    },
    [],
  );

  // Cədvəlin başının hədəf scroll-Y-i (sticky header qədər boşluq buraxır).
  function tableTopY(): number {
    const el = tableRef.current;
    if (!el) return window.scrollY;
    const header = document.querySelector("header");
    const offset = (header?.offsetHeight ?? 64) + 12;
    return el.getBoundingClientRect().top + window.scrollY - offset;
  }

  // Sabit-müddətli, eased (easeInOutCubic) yuxarı scroll — native smooth-scroll-un
  // uzun məsafədə "atma" hissini aradan qaldırır (sürət ramp-up/ramp-down). rAF.
  function animateScrollTo(targetY: number, duration: number, onDone: () => void) {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    const startY = window.scrollY;
    const dist = targetY - startY;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || Math.abs(dist) < 2) {
      window.scrollTo(0, targetY);
      onDone();
      return;
    }
    const ease = (t: number) =>
      t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    let startT: number | null = null;
    const step = (ts: number) => {
      if (startT === null) startT = ts;
      const p = Math.min(1, (ts - startT) / duration);
      window.scrollTo(0, startY + dist * ease(p));
      if (p < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        rafRef.current = null;
        onDone();
      }
    };
    rafRef.current = requestAnimationFrame(step);
  }

  // Aç → dərhal göstər (fade-up).
  // Bağla → sıralar fade-out + EYNİ VAXTDA cədvəl başına yumşaq, eased qayıdış
  // (vahid hərəkət); scroll bitəndə sıralar silinir. Silinən sıralar viewport-un
  // altında qaldığı üçün sonda görünən sıçrayış olmur.
  function toggleShowAll() {
    if (collapsing) return;
    if (!showAll) {
      setShowAll(true);
      return;
    }
    setCollapsing(true);
    // `remove` yalnız bir dəfə işləsin — rAF tamamlanması VƏ təhlükəsizlik
    // taymeri eyni vaxtda çağıra bilər (rAF gizli tab-da dayanarsa kilidlənmə yox).
    let done = false;
    const remove = () => {
      if (done) return;
      done = true;
      setShowAll(false);
      setCollapsing(false);
    };
    const target = tableTopY();
    const dist = window.scrollY - target;
    if (dist < 2) {
      // Artıq yuxarıdayıq — scroll lazım deyil, fade oynasın, sonra sil.
      window.setTimeout(remove, 300);
      return;
    }
    // Yumşaq, məsafəyə görə amma klamplı müddət — heç vaxt "uçmur".
    const duration = Math.min(560, 300 + dist * 0.22);
    animateScrollTo(target, duration, remove);
    // rAF dayanarsa (tab gizli/throttle) UI ilişməsin — zəmanətli sil.
    window.setTimeout(remove, duration + 250);
  }

  const query = q.trim().toLowerCase();
  const view = useMemo(
    () =>
      rows.filter(
        (r) =>
          r.type === filter &&
          (!query ||
            r.label.toLowerCase().includes(query) ||
            r.key.toLowerCase().includes(query)),
      ),
    [rows, filter, query],
  );

  const LIMIT = 10;
  const visible = showAll ? view : view.slice(0, LIMIT);

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-6xl px-5 py-8">
        <div className="mb-5 flex items-center gap-2">
          <Coins size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("assets.title")}
          </h1>
        </div>

        {/* filtr + axtarış */}
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-1 rounded-xl border border-border bg-surface p-1">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                  filter === f
                    ? "bg-accent text-black"
                    : "text-muted hover:text-text"
                }`}
              >
                {t(`atype.${f}`)}
              </button>
            ))}
          </div>
          <div className="relative sm:w-64">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("picker.search")}
              className="w-full rounded-xl border border-border bg-surface py-2 pl-9 pr-3 text-sm focus:border-accent focus:outline-none"
            />
          </div>
        </div>

        {/* cədvəl */}
        <div
          ref={tableRef}
          className="overflow-hidden rounded-card border border-border"
        >
          <table className="w-full text-sm">
            <AssetTableHead />
            <tbody>
              {status === "loading" &&
                Array.from({ length: 10 }).map((_, i) => <SkeletonRow key={i} />)}

              {status === "ready" &&
                visible.map((r, i) => (
                  <AssetRow
                    key={r.key}
                    row={r}
                    rank={i + 1}
                    animClass={
                      i >= LIMIT ? (collapsing ? "fade-out" : "fade-up") : ""
                    }
                  />
                ))}

              {status === "ready" && view.length === 0 && (
                <tr className="border-t border-border">
                  <td colSpan={6} className="px-3 py-10 text-center text-sm text-muted">
                    {t("picker.none")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* daha çox / daha az göstər — yalnız 10-dan çox olanda */}
          {status === "ready" && view.length > LIMIT && (
            <button
              onClick={toggleShowAll}
              aria-expanded={showAll}
              className="flex w-full items-center justify-center gap-2 border-t border-border bg-surface py-2.5 text-xs font-medium text-muted transition-colors hover:bg-surface-hover hover:text-accent"
            >
              {showAll
                ? t("assets.showLess")
                : `${t("assets.showMore")} (${view.length - LIMIT})`}
              <ChevronDown
                size={15}
                className={`transition-transform duration-200 ${showAll ? "rotate-180" : ""}`}
              />
            </button>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
