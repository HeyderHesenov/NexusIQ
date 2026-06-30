"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Flame } from "lucide-react";
import type { Category, NewsItem } from "@/types";
import { getTrending, prefetchForecast } from "@/lib/api";
import { localizedNews } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { NewsBadges } from "@/components/news/NewsBadges";

/** Ən təsirli xəbərlər lenti — kateqoriya üzrə, üfüqi sürüşən. */
export function TrendingStrip({ category }: { category: Category }) {
  const { t } = useI18n();
  const [items, setItems] = useState<NewsItem[]>([]);

  useEffect(() => {
    getTrending(category, 8).then(setItems);
  }, [category]);

  if (items.length === 0) return null;

  return (
    <section className="mb-6">
      <div className="mb-3 flex items-center gap-2">
        <Flame size={16} className="text-accent" />
        <h2 className="text-sm font-semibold tracking-tight">
          {t("home.trending")}
        </h2>
      </div>
      <div className="no-scrollbar flex gap-3 overflow-x-auto pb-2">
        {items.map((n, i) => (
          <TrendCard key={n.id} news={n} rank={i + 1} />
        ))}
      </div>
    </section>
  );
}

function TrendCard({ news, rank }: { news: NewsItem; rank: number }) {
  const { lang } = useI18n();
  const { title } = localizedNews(news, lang);
  return (
    <Link
      href={`/news/${news.id}`}
      onMouseEnter={() => prefetchForecast(news.id, lang)}
      onFocus={() => prefetchForecast(news.id, lang)}
      className="group flex w-64 shrink-0 flex-col gap-2 rounded-card border border-border bg-surface p-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/50"
    >
      <div className="flex items-center gap-2">
        <span className="grid h-5 w-5 shrink-0 place-items-center rounded-md bg-accent/15 font-mono text-[11px] font-semibold text-accent">
          {rank}
        </span>
        <NewsBadges sentiment={news.sentiment} impact={news.impactScore} />
      </div>
      <p className="line-clamp-3 text-sm font-medium leading-snug text-text">
        {title}
      </p>
      <span className="mt-auto truncate text-[11px] text-muted">
        {news.source ?? "—"}
      </span>
    </Link>
  );
}
