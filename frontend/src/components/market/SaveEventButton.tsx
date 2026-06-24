"use client";

import { Bookmark } from "lucide-react";
import type { SavedEvent } from "@/types";
import { toggleSavedEvent, useSavedEvent } from "@/lib/savedEvents";
import { useI18n } from "@/lib/i18n";

/** Təqvim hadisəsini saxlama düyməsi. Link içində işləyir (klik ötürülmür). */
export function SaveEventButton({
  event,
}: {
  event: Omit<SavedEvent, "savedAt">;
}) {
  const { t } = useI18n();
  const on = useSavedEvent(event.id);

  function handle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    toggleSavedEvent(event);
  }

  return (
    <button
      onClick={handle}
      title={on ? t("bm.remove") : t("bm.add")}
      aria-label={on ? t("bm.remove") : t("bm.add")}
      className={`grid h-7 w-7 place-items-center rounded-lg border backdrop-blur transition-all duration-200 ${
        on
          ? "border-accent/60 bg-accent/15 text-accent"
          : "border-border bg-bg/80 text-muted hover:border-accent/40 hover:text-text"
      }`}
    >
      <Bookmark size={14} fill={on ? "currentColor" : "none"} />
    </button>
  );
}
