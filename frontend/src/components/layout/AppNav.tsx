"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bookmark, LogOut, Target } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { NewsSearch } from "@/components/search/NewsSearch";
import { NotifyBell } from "@/components/notifications/NotifyBell";
import { ThemeToggle } from "@/components/ThemeToggle";

const LINKS: { href: string; labelKey: string }[] = [
  { href: "/", labelKey: "nav.news" },
  { href: "/markets", labelKey: "nav.markets" },
  { href: "/watchlist", labelKey: "nav.watchlist" },
  { href: "/compare", labelKey: "nav.compare" },
  { href: "/correlation", labelKey: "corr.nav" },
];

function logout() {
  localStorage.removeItem("nexusiq_session");
  location.href = "/";
}

/** Bütün səhifələrdə paylaşılan üst naviqasiya. */
export function AppNav() {
  const { t } = useI18n();
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-5">
        {/* loqo */}
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="text-lg font-semibold tracking-tight">
            Nexus<span className="text-accent">IQ</span>
          </span>
        </Link>

        {/* səhifə keçidləri */}
        <nav className="hidden items-center gap-1 rounded-xl border border-border bg-surface p-1 lg:flex">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all duration-200 ${
                isActive(l.href)
                  ? "bg-accent text-black"
                  : "text-muted hover:bg-surface-hover hover:text-text"
              }`}
            >
              {t(l.labelKey)}
            </Link>
          ))}
        </nav>

        {/* sağ alətlər */}
        <div className="flex items-center gap-2">
          <NewsSearch />
          <Link
            href="/alerts"
            title={t("nav.alerts")}
            className="flex items-center rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-accent hover:text-accent"
          >
            <Target size={15} />
          </Link>
          <Link
            href="/saved"
            title={t("bm.title")}
            className="flex items-center rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-accent hover:text-accent"
          >
            <Bookmark size={15} />
          </Link>
          <NotifyBell />
          <ThemeToggle />
          <LanguageSwitcher />
          <button
            onClick={logout}
            title={t("header.logout")}
            className="flex items-center rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-down/50 hover:text-down"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>

      {/* mobil səhifə keçidləri */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-border px-3 py-2 lg:hidden">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
              isActive(l.href)
                ? "bg-accent text-black"
                : "text-muted hover:text-text"
            }`}
          >
            {t(l.labelKey)}
          </Link>
        ))}
      </nav>
    </header>
  );
}
