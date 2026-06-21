"use client";

import Link from "next/link";
import { ArrowLeft, Bookmark } from "lucide-react";
import { useBookmarkList } from "@/lib/bookmarks";
import { useI18n } from "@/lib/i18n";
import { NewsCard } from "@/components/news/NewsCard";

export default function SavedPage() {
  const { t } = useI18n();
  const items = useBookmarkList();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-5">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-colors hover:border-accent hover:text-text"
          >
            <ArrowLeft size={15} />
            {t("news.back")}
          </Link>
          <div className="flex items-center gap-2">
            <Bookmark size={16} className="text-accent" />
            <span className="text-lg font-semibold tracking-tight">
              {t("bm.title")}
            </span>
            {items.length > 0 && (
              <span className="font-mono text-xs text-muted">
                {items.length}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border py-24 text-center">
            <Bookmark size={28} className="mb-3 text-muted" />
            <p className="text-base font-medium text-text">{t("bm.empty")}</p>
            <p className="mt-1.5 max-w-sm text-sm text-muted">
              {t("bm.emptyHint")}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((n) => (
              <NewsCard key={n.id} news={n} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
