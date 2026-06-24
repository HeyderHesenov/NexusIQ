"use client";

import Link from "next/link";
import { Bookmark } from "lucide-react";
import { useBookmarkList } from "@/lib/bookmarks";
import { useSavedEventList } from "@/lib/savedEvents";
import { useI18n } from "@/lib/i18n";

/** Header /saved linki — saxlanan xəbər + hadisə sayını canlı nişanla göstərir. */
export function SavedNavLink() {
  const { t } = useI18n();
  const total = useBookmarkList().length + useSavedEventList().length;

  return (
    <Link
      href="/saved"
      title={t("bm.title")}
      className="relative flex items-center rounded-lg px-2 py-1.5 text-muted transition-colors duration-200 hover:bg-surface-hover hover:text-accent"
    >
      <Bookmark size={16} />
      {total > 0 && (
        <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-accent px-1 font-mono text-[10px] font-semibold leading-none text-black">
          {total > 9 ? "9+" : total}
        </span>
      )}
    </Link>
  );
}
