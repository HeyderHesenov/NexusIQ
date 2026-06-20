"use client";

import { LogOut, MessageSquare } from "lucide-react";
import type { Category } from "@/types";
import { useI18n } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

const TABS: { key: Category; label: string }[] = [
  { key: "forex", label: "Forex" },
  { key: "us", label: "US Markets" },
  { key: "crypto", label: "Crypto" },
];

export function Header({
  active,
  onChange,
  onLogout,
}: {
  active: Category;
  onChange: (c: Category) => void;
  onLogout: () => void;
}) {
  const { t } = useI18n();
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
        {/* loqo */}
        <div className="flex items-center gap-2.5">
          <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="text-lg font-semibold tracking-tight">
            Nexus<span className="text-accent">FX</span>
          </span>
        </div>

        {/* kateqoriya tabları */}
        <nav className="hidden items-center gap-1 rounded-xl border border-border bg-surface p-1 md:flex">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => onChange(t.key)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-200 ${
                active === t.key
                  ? "bg-accent text-black"
                  : "text-muted hover:bg-surface-hover hover:text-text"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* sağ tərəf */}
        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-accent hover:text-text"
            title={t("header.aiAnalyst")}
          >
            <MessageSquare size={15} />
            <span className="hidden sm:inline">{t("header.aiAnalyst")}</span>
          </button>
          <LanguageSwitcher />
          <button
            onClick={onLogout}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-down/50 hover:text-down"
            title={t("header.logout")}
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>

      {/* mobil tablar */}
      <nav className="flex items-center gap-1 border-t border-border px-3 py-2 md:hidden">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
              active === t.key
                ? "bg-accent text-black"
                : "text-muted hover:text-text"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
