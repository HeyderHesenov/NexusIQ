"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bookmark, ChevronDown, LogOut, Target } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { NewsSearch } from "@/components/search/NewsSearch";
import { NotifyBell } from "@/components/notifications/NotifyBell";
import { ThemeToggle } from "@/components/ThemeToggle";

type Leaf = { href: string; labelKey: string };
type NavItem =
  | { kind: "link"; href: string; labelKey: string }
  | { kind: "group"; labelKey: string; items: Leaf[] };

const NAV: NavItem[] = [
  { kind: "link", href: "/", labelKey: "nav.news" },
  {
    kind: "group",
    labelKey: "navg.market",
    items: [
      { href: "/assets", labelKey: "nav.assets" },
      { href: "/markets", labelKey: "nav.markets" },
      { href: "/watchlist", labelKey: "nav.watchlist" },
    ],
  },
  {
    kind: "group",
    labelKey: "navg.analysis",
    items: [
      { href: "/anomalies", labelKey: "anom.nav" },
      { href: "/compare", labelKey: "nav.compare" },
      { href: "/correlation", labelKey: "corr.nav" },
      { href: "/powerlaw", labelKey: "pl.nav" },
    ],
  },
];

const ALL_LEAVES: Leaf[] = [
  { href: "/", labelKey: "nav.news" },
  { href: "/assets", labelKey: "nav.assets" },
  { href: "/markets", labelKey: "nav.markets" },
  { href: "/watchlist", labelKey: "nav.watchlist" },
  { href: "/anomalies", labelKey: "anom.nav" },
  { href: "/compare", labelKey: "nav.compare" },
  { href: "/correlation", labelKey: "corr.nav" },
  { href: "/powerlaw", labelKey: "pl.nav" },
];

function logout() {
  localStorage.removeItem("nexusiq_session");
  location.href = "/";
}

const isActive = (pathname: string, href: string) =>
  href === "/" ? pathname === "/" : pathname.startsWith(href);

export function AppNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const navRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenGroup(null);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  useEffect(() => setOpenGroup(null), [pathname]);

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-5">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="text-lg font-semibold tracking-tight">
            Nexus<span className="text-accent">IQ</span>
          </span>
        </Link>

        {/* qruplaşmış naviqasiya */}
        <nav
          ref={navRef}
          className="hidden items-center gap-1 rounded-xl border border-border bg-surface p-1 md:flex"
        >
          {NAV.map((item) =>
            item.kind === "link" ? (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all ${
                  isActive(pathname, item.href)
                    ? "bg-accent text-black"
                    : "text-muted hover:bg-surface-hover hover:text-text"
                }`}
              >
                {t(item.labelKey)}
              </Link>
            ) : (
              <div key={item.labelKey} className="relative">
                <button
                  onClick={() =>
                    setOpenGroup((g) => (g === item.labelKey ? null : item.labelKey))
                  }
                  className={`flex items-center gap-1 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all ${
                    item.items.some((l) => isActive(pathname, l.href))
                      ? "bg-accent/15 text-accent"
                      : "text-muted hover:bg-surface-hover hover:text-text"
                  }`}
                >
                  {t(item.labelKey)}
                  <ChevronDown
                    size={13}
                    className={`transition-transform duration-200 ${
                      openGroup === item.labelKey ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {openGroup === item.labelKey && (
                  <div className="absolute left-0 z-40 mt-2 w-44 overflow-hidden rounded-xl border border-border bg-surface shadow-2xl fade-up">
                    {item.items.map((l) => (
                      <Link
                        key={l.href}
                        href={l.href}
                        className={`block px-4 py-2.5 text-sm transition-colors hover:bg-surface-hover ${
                          isActive(pathname, l.href) ? "text-accent" : "text-text"
                        }`}
                      >
                        {t(l.labelKey)}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ),
          )}
        </nav>

        {/* sağ alətlər */}
        <div className="flex items-center gap-2">
          <NewsSearch />
          <Link
            href="/alerts"
            title={t("nav.alerts")}
            className="flex items-center rounded-lg px-2 py-1.5 text-muted transition-colors duration-200 hover:bg-surface-hover hover:text-accent"
          >
            <Target size={16} />
          </Link>
          <Link
            href="/saved"
            title={t("bm.title")}
            className="flex items-center rounded-lg px-2 py-1.5 text-muted transition-colors duration-200 hover:bg-surface-hover hover:text-accent"
          >
            <Bookmark size={16} />
          </Link>
          <NotifyBell />
          <ThemeToggle />
          <LanguageSwitcher />
          <button
            onClick={logout}
            title={t("header.logout")}
            className="flex items-center rounded-lg px-2 py-1.5 text-muted transition-colors duration-200 hover:bg-surface-hover hover:text-down"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>

      {/* mobil — bütün keçidlər düz sıra */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-border px-3 py-2 md:hidden">
        {ALL_LEAVES.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
              isActive(pathname, l.href)
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
