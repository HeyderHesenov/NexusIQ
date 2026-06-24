"use client";

import { useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import type { Asset } from "@/types";
import { useI18n } from "@/lib/i18n";
import { useClickOutside } from "@/lib/useClickOutside";

// Tam tip sırası — AssetPicker-dən fərqli olaraq HEÇ bir tip düşmür (stock/industrial daxil).
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
 * Tək-seçim aktiv combobox — trigger seçilmiş aktivi göstərir, klikdə axtarışlı +
 * kateqoriyalı üzən panel açılır. Siqnal (alert) formu üçün. Seçimdə bağlanır.
 */
export function AssetSelect({
  assets,
  value,
  onChange,
}: {
  assets: Asset[];
  value: string;
  onChange: (key: string) => void;
}) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));

  const selectedLabel = assets.find((a) => a.key === value)?.label ?? value;

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
    // Tanınan tiplər sıra ilə, sonra qalan hər tip — heç bir aktiv itməsin.
    const order = [
      ...TYPE_ORDER,
      ...Object.keys(by).filter((tp) => !TYPE_ORDER.includes(tp as never)),
    ];
    return order
      .filter((tp) => by[tp]?.length)
      .map((tp) => ({ type: tp, items: by[tp] }));
  }, [assets, query]);

  function pick(key: string) {
    onChange(key);
    setOpen(false);
    setQ("");
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex min-w-40 items-center justify-between gap-2 rounded-lg border border-border bg-bg px-3 py-2 text-sm transition-colors hover:border-accent/60 focus:border-accent focus:outline-none"
      >
        <span className="font-medium">{selectedLabel}</span>
        <ChevronDown
          size={15}
          className={`shrink-0 text-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute z-30 mt-2 max-h-72 w-60 overflow-y-auto rounded-xl border border-border bg-surface py-1 shadow-2xl fade-up">
          <div className="sticky top-0 bg-surface px-1.5 pb-1.5 pt-1">
            <div className="relative">
              <Search
                size={15}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"
              />
              <input
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t("picker.search")}
                className="w-full rounded-lg border border-border bg-bg py-2 pl-8 pr-2 text-sm text-text placeholder:text-muted/70 focus:border-accent focus:outline-none"
              />
            </div>
          </div>

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
                const on = a.key === value;
                return (
                  <button
                    key={a.key}
                    type="button"
                    onClick={() => pick(a.key)}
                    className={`flex w-full items-center justify-between px-4 py-2 text-sm transition-colors hover:bg-surface-hover ${
                      on ? "text-accent" : "text-text"
                    }`}
                  >
                    <span className="font-medium">{a.label}</span>
                    {on && <Check size={15} className="shrink-0" />}
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
