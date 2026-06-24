"use client";

import { useMemo, useRef, useState } from "react";
import { Check, Plus, Search } from "lucide-react";
import type { Asset } from "@/types";
import { useI18n } from "@/lib/i18n";
import { useClickOutside } from "@/lib/useClickOutside";

const TYPE_ORDER = [
  "crypto",
  "stock",
  "index",
  "forex",
  "metal",
  "commodity",
  "industrial",
] as const;

/**
 * Minimalist aktiv seçici — axtarış sahəsi + tələb üzrə açılan tək sütunlu
 * nəticə paneli (üzən). Fokus və ya yazı olmayanda panel bağlıdır, ona görə
 * səhifə təmiz qalır. İzləmə və Müqayisə üçün paylaşılır.
 */
export function AssetPicker({
  assets,
  isSelected,
  onToggle,
  disableUnselected = false,
}: {
  assets: Asset[];
  isSelected: (key: string) => boolean;
  onToggle: (key: string) => void;
  disableUnselected?: boolean;
}) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));

  const query = q.trim().toLowerCase();
  const groups = useMemo(() => {
    const filtered = query
      ? assets.filter(
          (a) =>
            a.label.toLowerCase().includes(query) ||
            a.key.toLowerCase().includes(query),
        )
      : assets;
    const by: Record<string, Asset[]> = {};
    for (const a of filtered) (by[a.type] ??= []).push(a);
    return TYPE_ORDER.filter((tp) => by[tp]?.length).map((tp) => ({
      type: tp,
      items: by[tp],
    }));
  }, [assets, query]);

  return (
    <div ref={ref} className="relative">
      <div className="relative">
        <Search
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          value={q}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          placeholder={t("picker.search")}
          className="w-full rounded-xl border border-border bg-surface py-2.5 pl-9 pr-3 text-sm text-text placeholder:text-muted/70 focus:border-accent focus:outline-none"
        />
      </div>

      {open && (
        <div className="absolute z-30 mt-2 max-h-72 w-full overflow-y-auto rounded-xl border border-border bg-surface py-1 shadow-2xl fade-up">
          {groups.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-muted">
              {t("picker.none")}
            </p>
          )}
          {groups.map((g) => (
            <div key={g.type}>
              <p className="px-4 pb-1 pt-2 font-mono text-[10px] uppercase tracking-wider text-muted/70">
                {t(`atype.${g.type}`)}
              </p>
              {g.items.map((a) => {
                const on = isSelected(a.key);
                const dim = disableUnselected && !on;
                return (
                  <button
                    key={a.key}
                    onClick={() => !dim && onToggle(a.key)}
                    disabled={dim}
                    className={`flex w-full items-center justify-between px-4 py-2 text-sm transition-colors ${
                      dim
                        ? "cursor-not-allowed text-muted/40"
                        : "hover:bg-surface-hover"
                    } ${on ? "text-accent" : "text-text"}`}
                  >
                    <span className="font-medium">{a.label}</span>
                    {on ? (
                      <Check size={15} className="shrink-0" />
                    ) : (
                      <Plus size={15} className="shrink-0 text-muted" />
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
