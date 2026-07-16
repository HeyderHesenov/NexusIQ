"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { Ticker } from "@/components/market/Ticker";
import { NewsCard } from "@/components/news/NewsCard";
import { RelevantToMe } from "@/components/home/RelevantToMe";
import { TrendingStrip } from "@/components/news/TrendingStrip";
import { CategorySelect } from "@/components/news/CategorySelect";
import { apiGet, getNewsCount } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Category, NewsItem } from "@/types";

const PAGE_SIZE = 30;

// Modul-səviyyə keş (naviqasiyalar arası yaşayır) — '/'-ə qayıdanda 9 skeleton
// yerinə dərhal əvvəlki xəbərləri göstər, sonra fonda təzələ (reload hissi yox).
const _newsCache = new Map<string, NewsItem[]>();

export default function HomePage() {
  const { t } = useI18n();
  const [active, setActive] = useState<Category>("forex");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<NewsItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  // Backend qısa müddət əlçatmaz olsa, feed özü sağalsın — geriçəkilmə ilə
  // avtomatik yenidən cəhd (3s, 6s, 12s). Uğurda və ya tab/səhifə dəyişəndə sıfırlanır.
  const retryRef = useRef<{ timer?: ReturnType<typeof setTimeout>; n: number }>({
    n: 0,
  });
  // Hər yükləmə "nəsil" nömrəsi alır. Tab/səhifə dəyişəndə və ya unmount-da nömrə
  // artır; gec gələn (köhnə) sorğu/retry nəticəsi atılır — stale state yazılmasın.
  const genRef = useRef(0);

  const cancelRetry = useCallback(() => {
    if (retryRef.current.timer) clearTimeout(retryRef.current.timer);
    retryRef.current = { n: 0 };
  }, []);

  const load = useCallback(async (cat: Category, pg: number, gen: number) => {
    if (gen !== genRef.current) return; // stale (köhnə retry/keçid)
    const cacheKey = `${cat}:${pg}`;
    const cached = _newsCache.get(cacheKey);
    if (cached) {
      // Keşdən dərhal göstər (skeleton yox), aşağıda fonda təzələ.
      setItems(cached);
      setStatus("ready");
    } else {
      setStatus("loading");
    }
    try {
      const offset = (pg - 1) * PAGE_SIZE;
      const data = await apiGet<NewsItem[]>(
        `/news?category=${cat}&limit=${PAGE_SIZE}&offset=${offset}`,
      );
      if (gen !== genRef.current) return; // bu arada keçid oldu — nəticəni at
      _newsCache.set(cacheKey, data);
      setItems(data);
      setStatus("ready");
      retryRef.current.n = 0; // uğur — sayğacı sıfırla
    } catch {
      if (gen !== genRef.current) return; // stale xəta — state/retry yazma
      if (cached) return; // köhnə keş göstərilir — xəta ekranına keçmə
      setStatus("error");
      const n = retryRef.current.n;
      if (n < 3) {
        const delay = 3000 * 2 ** n; // 3s, 6s, 12s
        retryRef.current.n = n + 1;
        retryRef.current.timer = setTimeout(() => load(cat, pg, gen), delay);
      }
    }
  }, []);

  // kateqoriya dəyişəndə ümumi sayı yenilə
  useEffect(() => {
    getNewsCount(active).then(setTotal);
  }, [active]);

  // kateqoriya və ya səhifə dəyişəndə xəbərləri çək (köhnə retry/sorğuları ləğv et)
  useEffect(() => {
    cancelRetry();
    const gen = ++genRef.current;
    load(active, page, gen);
    // unmount/keçiddə nəsli artır — gec gələn sorğu/retry stale sayılıb atılır
    return () => {
      genRef.current++;
      cancelRetry();
    };
  }, [active, page, load, cancelRetry]);

  function changeTab(c: Category) {
    setActive(c);
    setPage(1);
  }

  function goToPage(pg: number) {
    setPage(pg);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <Ticker />

      <main className="shell py-8 flex-1">
        {page === 1 && <RelevantToMe />}

        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
              {t(`tab.${active}`)}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {t("home.marketNews")}
            </h1>
          </div>
          <CategorySelect active={active} onChange={changeTab} />
        </div>

        {page === 1 && <TrendingStrip category={active} />}

        {status === "loading" && (
          <NewsGrid>
            {Array.from({ length: 9 }).map((_, i) => (
              <NewsCardSkeleton key={i} />
            ))}
          </NewsGrid>
        )}

        {status === "error" && (
          <EmptyState
            title={t("home.error")}
            hint={t("home.errorHint")}
            onRetry={() => {
              cancelRetry();
              load(active, page, ++genRef.current);
            }}
            retryLabel={t("home.retry")}
          />
        )}

        {status === "ready" && items.length === 0 && (
          <EmptyState title={t("home.empty")} hint={t("home.emptyHint")} />
        )}

        {status === "ready" && items.length > 0 && (
          <NewsGrid>
            {items.map((n) => (
              <NewsCard key={n.id} news={n} />
            ))}
          </NewsGrid>
        )}

        {status !== "loading" && totalPages > 1 && (
          <Pagination page={page} totalPages={totalPages} onGo={goToPage} />
        )}
      </main>

      <Footer />
    </div>
  );
}

/** Səhifə nömrələri — siyahının altında. Çox səhifə olsa pəncərələnir (… ilə). */
function Pagination({
  page,
  totalPages,
  onGo,
}: {
  page: number;
  totalPages: number;
  onGo: (p: number) => void;
}) {
  // göstəriləcək səhifə nömrələri (cari ətrafında pəncərə + ilk/son)
  const nums: (number | "…")[] = [];
  const push = (n: number | "…") => nums.push(n);
  const win = 1;
  for (let p = 1; p <= totalPages; p++) {
    if (p === 1 || p === totalPages || (p >= page - win && p <= page + win)) {
      push(p);
    } else if (nums[nums.length - 1] !== "…") {
      push("…");
    }
  }

  const base =
    "min-w-9 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors duration-150";

  return (
    <nav className="mt-10 flex items-center justify-center gap-1.5">
      <button
        onClick={() => onGo(page - 1)}
        disabled={page <= 1}
        className={`${base} border-border bg-surface text-muted hover:border-accent hover:text-text disabled:cursor-not-allowed disabled:opacity-40`}
      >
        ‹
      </button>

      {nums.map((n, i) =>
        n === "…" ? (
          <span key={`e${i}`} className="px-1.5 text-sm text-muted">
            …
          </span>
        ) : (
          <button
            key={n}
            onClick={() => onGo(n)}
            className={`${base} ${
              n === page
                ? "border-accent bg-accent text-black"
                : "border-border bg-surface text-muted hover:border-accent hover:text-text"
            }`}
          >
            {n}
          </button>
        ),
      )}

      <button
        onClick={() => onGo(page + 1)}
        disabled={page >= totalPages}
        className={`${base} border-border bg-surface text-muted hover:border-accent hover:text-text disabled:cursor-not-allowed disabled:opacity-40`}
      >
        ›
      </button>
    </nav>
  );
}

function NewsGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 3xl:grid-cols-5 4xl:grid-cols-6">
      {children}
    </div>
  );
}

function EmptyState({
  title,
  hint,
  onRetry,
  retryLabel,
}: {
  title: string;
  hint?: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border py-20 text-center">
      <p className="text-base font-medium text-text">{title}</p>
      {hint && <p className="mt-1.5 max-w-sm text-sm text-muted">{hint}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 rounded-lg border border-border bg-surface px-4 py-2 text-sm text-text transition-colors hover:border-accent hover:text-accent"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}

/** Xəbər kartının yüklənmə skeleti (shimmer). */
function NewsCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-card border border-border bg-surface">
      <div className="aspect-[16/9] animate-pulse bg-surface-hover" />
      <div className="space-y-3 p-4">
        <div className="h-4 w-full animate-pulse rounded bg-surface-hover" />
        <div className="h-4 w-4/5 animate-pulse rounded bg-surface-hover" />
        <div className="h-3 w-1/3 animate-pulse rounded bg-surface-hover" />
      </div>
    </div>
  );
}
