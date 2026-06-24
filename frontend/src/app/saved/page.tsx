"use client";

import Link from "next/link";
import { Bookmark } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { useBookmarkList } from "@/lib/bookmarks";
import { useSavedEventList } from "@/lib/savedEvents";
import { useI18n } from "@/lib/i18n";
import { NewsCard } from "@/components/news/NewsCard";
import { SaveEventButton } from "@/components/market/SaveEventButton";
import type { SavedEvent } from "@/types";

export default function SavedPage() {
  const { t } = useI18n();
  const news = useBookmarkList();
  const events = useSavedEventList();

  const total = news.length + events.length;
  // Alt-başlıqlar yalnız hər iki tip mövcud olduqda — tək tipdə sadə görünüş.
  const showHeads = news.length > 0 && events.length > 0;

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />

      <main className="mx-auto w-full max-w-7xl px-5 py-8">
        <div className="mb-6 flex items-center gap-2">
          <Bookmark size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">{t("bm.title")}</h1>
          {total > 0 && (
            <span className="font-mono text-xs text-muted">{total}</span>
          )}
        </div>

        {total === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-border py-24 text-center">
            <Bookmark size={28} className="mb-3 text-muted" />
            <p className="text-base font-medium text-text">{t("bm.empty")}</p>
            <p className="mt-1.5 max-w-sm text-sm text-muted">{t("bm.emptyHint")}</p>
          </div>
        ) : (
          <div className="space-y-8">
            {events.length > 0 && (
              <section>
                {showHeads && (
                  <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.15em] text-accent">
                    {t("bm.eventsTitle")}
                  </h2>
                )}
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {events.map((ev) => (
                    <SavedEventCard key={ev.id} event={ev} />
                  ))}
                </div>
              </section>
            )}

            {news.length > 0 && (
              <section>
                {showHeads && (
                  <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.15em] text-accent">
                    {t("bm.newsTitle")}
                  </h2>
                )}
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {news.map((n) => (
                    <NewsCard key={n.id} news={n} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}

/** Saxlanan təqvim hadisəsi — /brief-ə link + silmə düyməsi. */
function SavedEventCard({ event }: { event: SavedEvent }) {
  return (
    <div className="group relative">
      <Link
        href={event.href}
        target="_blank"
        className="flex h-full flex-col gap-2 rounded-card border border-border bg-surface px-4 py-3.5 transition-colors duration-150 hover:border-accent/60"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-wider text-accent">
            {event.badge}
          </span>
        </div>
        <p className="line-clamp-2 text-sm font-medium leading-snug text-text">
          {event.name}
        </p>
        <span className="mt-auto truncate font-mono text-[11px] text-muted">
          {event.sub}
        </span>
      </Link>
      <div className="absolute right-2 top-2">
        <SaveEventButton event={event} />
      </div>
    </div>
  );
}
