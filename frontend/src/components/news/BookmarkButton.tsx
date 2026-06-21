"use client";

import { Bookmark } from "lucide-react";
import type { NewsItem } from "@/types";
import { toggleBookmark, useBookmark } from "@/lib/bookmarks";
import { useI18n } from "@/lib/i18n";

/** Xəbəri yadda saxlama düyməsi. Link içində işləyir (klik ötürülmür). */
export function BookmarkButton({
  news,
  size = "sm",
}: {
  news: NewsItem;
  size?: "sm" | "md";
}) {
  const { t } = useI18n();
  const on = useBookmark(news.id);

  function handle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    toggleBookmark(news);
  }

  const dim = size === "md" ? "h-9 w-9" : "h-8 w-8";
  const icon = size === "md" ? 17 : 15;

  return (
    <button
      onClick={handle}
      title={on ? t("bm.remove") : t("bm.add")}
      aria-label={on ? t("bm.remove") : t("bm.add")}
      className={`grid ${dim} place-items-center rounded-lg border backdrop-blur transition-all duration-200 ${
        on
          ? "border-accent/60 bg-accent/15 text-accent"
          : "border-border bg-bg/70 text-muted hover:text-text hover:border-accent/40"
      }`}
    >
      <Bookmark size={icon} fill={on ? "currentColor" : "none"} />
    </button>
  );
}
