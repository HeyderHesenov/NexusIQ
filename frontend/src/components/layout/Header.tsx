"use client";

import Link from "next/link";
import { Activity, LogOut } from "lucide-react";
import type { Category } from "@/types";
import { useI18n } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { NewsSearch } from "@/components/search/NewsSearch";
import { NotifyBell } from "@/components/notifications/NotifyBell";

const TABS: { key: Category; labelKey: string }[] = [
  { key: "forex", labelKey: "tab.forex" },
  { key: "us", labelKey: "tab.us" },
  { key: "crypto", labelKey: "tab.crypto" },
  { key: "commodities", labelKey: "tab.commodities" },
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
            Nexus<span className="text-accent">IQ</span>
          </span>
        </div>

        {/* kateqoriya tabları */}
        <nav className="hidden items-center gap-1 rounded-xl border border-border bg-surface p-1 md:flex">
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
        </nav>

        {/* sağ tərəf */}
        <div className="flex items-center gap-2">
          <NewsSearch />
          <Link
            href="/correlation"
            title={t("corr.nav")}
            className="flex items-center rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-accent hover:text-accent"
          >
            <Activity size={15} />
          </Link>
          <NotifyBell />
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
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
              active === tab.key
                ? "bg-accent text-black"
                : "text-muted hover:text-text"
            }`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </nav>
    </header>
  );
}
