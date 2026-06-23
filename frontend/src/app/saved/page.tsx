"use client";

import { Bookmark } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { useBookmarkList } from "@/lib/bookmarks";
import { useI18n } from "@/lib/i18n";
import { NewsCard } from "@/components/news/NewsCard";

export default function SavedPage() {
  const { t } = useI18n();
  const items = useBookmarkList();

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />

      <main className="mx-auto w-full max-w-7xl px-5 py-8">
        <div className="mb-6 flex items-center gap-2">
          <Bookmark size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("bm.title")}
          </h1>
          {items.length > 0 && (
            <span className="font-mono text-xs text-muted">{items.length}</span>
          )}
        </div>
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
      <Footer />
    </div>
  );
}
