"use client";

import Link from "next/link";
import type { NewsItem, Category } from "@/types";
import { formatDateTime, localizedNews } from "@/lib/utils";
import { prefetchForecast } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { NewsImage } from "@/components/news/NewsImage";
import { NewsBadges } from "@/components/news/NewsBadges";
import { BookmarkButton } from "@/components/news/BookmarkButton";

const CAT_LABEL: Record<Category, string> = {
  forex: "Forex",
  us: "US",
  crypto: "Crypto",
  commodities: "Commodities",
};

/** Bir xəbər kartı — şəkil, kateqoriya, başlıq, xülasə, mənbə + tarix. */
export function NewsCard({ news }: { news: NewsItem }) {
  const { lang } = useI18n();
  const { title, body } = localizedNews(news, lang);
  return (
    <Link
      href={`/news/${news.id}`}
      target="_blank"
      onMouseEnter={() => prefetchForecast(news.id, lang)}
      onFocus={() => prefetchForecast(news.id, lang)}
      className="group flex flex-col overflow-hidden rounded-card border border-border bg-surface transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-[0_12px_30px_-12px_var(--shadow)]"
    >
      {/* real şəkil (alınmasa generativ fallback) */}
      <div className="relative aspect-[16/9] overflow-hidden bg-surface-hover">
        <NewsImage
          src={news.imageUrl}
          seed={news.id}
          category={news.category}
          className="h-full w-full transition-transform duration-500 group-hover:scale-105"
        />
        <span className="absolute left-3 top-3 rounded-md bg-bg/80 px-2 py-1 font-mono text-[10px] font-medium uppercase tracking-wider text-accent backdrop-blur">
          {CAT_LABEL[news.category]}
        </span>
        {/* desktop: yalnız hover/fokusda görünür */}
        <div className="absolute right-3 top-3 hidden opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100 sm:block">
          <BookmarkButton news={news} />
        </div>
      </div>

      {/* mətn */}
      <div className="flex flex-1 flex-col p-4">
        <h3 className="line-clamp-2 font-semibold leading-snug tracking-tight text-text">
          {title}
        </h3>
        {body && (
          <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">
            {body}
          </p>
        )}
        <div className="mt-3">
          <NewsBadges sentiment={news.sentiment} impact={news.impactScore} />
        </div>
        <div className="mt-3 flex items-center justify-between gap-2 border-t border-border pt-3">
          <span className="truncate text-xs font-medium text-muted">
            {news.source ?? "—"}
          </span>
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="font-mono text-[11px] text-muted">
              {formatDateTime(news.publishedAt)}
            </span>
            {/* mobil: əlfəcin həmişə altda görünür (şəklin üstündə yox) */}
            <span className="sm:hidden">
              <BookmarkButton news={news} />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
