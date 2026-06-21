"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Layers } from "lucide-react";
import type { Category } from "@/types";
import { useI18n } from "@/lib/i18n";

const TABS: { key: Category; labelKey: string }[] = [
  { key: "forex", labelKey: "tab.forex" },
  { key: "us", labelKey: "tab.us" },
  { key: "crypto", labelKey: "tab.crypto" },
  { key: "commodities", labelKey: "tab.commodities" },
];

/** Kateqoriya seçici — 4 tabı bir kompakt dropdown-da yığır. */
export function CategorySelect({
  active,
  onChange,
}: {
  active: Category;
  onChange: (c: Category) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3.5 py-2 text-sm font-medium text-text transition-colors hover:border-accent/50"
      >
        <Layers size={15} className="text-accent" />
        {t(`tab.${active}`)}
        <ChevronDown
          size={14}
          className={`text-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-48 overflow-hidden rounded-xl border border-border bg-surface shadow-2xl fade-up">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                onChange(tab.key);
                setOpen(false);
              }}
              className={`flex w-full items-center justify-between px-4 py-2.5 text-sm transition-colors hover:bg-surface-hover ${
                active === tab.key ? "text-accent" : "text-text"
              }`}
            >
              {t(tab.labelKey)}
              {active === tab.key && <Check size={15} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
