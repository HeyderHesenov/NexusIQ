"use client";

import type { Category } from "@/types";
import { useI18n } from "@/lib/i18n";

const TABS: { key: Category; labelKey: string }[] = [
  { key: "forex", labelKey: "tab.forex" },
  { key: "us", labelKey: "tab.us" },
  { key: "crypto", labelKey: "tab.crypto" },
  { key: "commodities", labelKey: "tab.commodities" },
];

/** Xəbər kateqoriya filtri — yalnız xəbər lentində. */
export function CategoryTabs({
  active,
  onChange,
}: {
  active: Category;
  onChange: (c: Category) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-xl border border-border bg-surface p-1">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-200 ${
            active === tab.key
              ? "bg-accent text-black"
              : "text-muted hover:bg-surface-hover hover:text-text"
          }`}
        >
          {t(tab.labelKey)}
        </button>
      ))}
    </div>
  );
}
