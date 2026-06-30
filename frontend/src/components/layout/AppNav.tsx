"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  CalendarDays,
  ChevronDown,
  Coins,
  GitCompareArrows,
  History,
  Info,
  LogOut,
  Newspaper,
  Radar,
  Spline,
  Star,
  Target,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { prefetchAnomalies } from "@/lib/api";
import { useClickOutside } from "@/lib/useClickOutside";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { NewsSearch } from "@/components/search/NewsSearch";
import { SavedNavLink } from "@/components/layout/SavedNavLink";
import { NotifyBell } from "@/components/notifications/NotifyBell";
import { ThemeToggle } from "@/components/ThemeToggle";

type Leaf = { href: string; labelKey: string; icon: LucideIcon };
type NavItem =
  | { kind: "link"; href: string; labelKey: string; icon: LucideIcon }
  | { kind: "group"; labelKey: string; items: Leaf[] };

const NAV: NavItem[] = [
  { kind: "link", href: "/", labelKey: "nav.news", icon: Newspaper },
  { kind: "link", href: "/radar", labelKey: "nav.radar", icon: Radar },
  {
    kind: "group",
    labelKey: "navg.market",
    items: [
      { href: "/assets", labelKey: "nav.assets", icon: Coins },
      { href: "/markets", labelKey: "nav.markets", icon: CalendarDays },
      { href: "/watchlist", labelKey: "nav.watchlist", icon: Star },
    ],
  },
  {
    kind: "group",
    labelKey: "navg.analysis",
    items: [
      { href: "/anomalies", labelKey: "anom.nav", icon: Activity },
      { href: "/analogs", labelKey: "analog.nav", icon: History },
      { href: "/compare", labelKey: "nav.compare", icon: GitCompareArrows },
      { href: "/correlation", labelKey: "corr.nav", icon: Spline },
      { href: "/powerlaw", labelKey: "pl.nav", icon: TrendingUp },
    ],
  },
  { kind: "link", href: "/about", labelKey: "about.nav", icon: Info },
];

const ALL_LEAVES: Leaf[] = [
  { href: "/", labelKey: "nav.news", icon: Newspaper },
  { href: "/radar", labelKey: "nav.radar", icon: Radar },
  { href: "/assets", labelKey: "nav.assets", icon: Coins },
  { href: "/markets", labelKey: "nav.markets", icon: CalendarDays },
  { href: "/watchlist", labelKey: "nav.watchlist", icon: Star },
  { href: "/anomalies", labelKey: "anom.nav", icon: Activity },
  { href: "/analogs", labelKey: "analog.nav", icon: History },
  { href: "/compare", labelKey: "nav.compare", icon: GitCompareArrows },
  { href: "/correlation", labelKey: "corr.nav", icon: Spline },
  { href: "/powerlaw", labelKey: "pl.nav", icon: TrendingUp },
  { href: "/about", labelKey: "about.nav", icon: Info },
];

function logout() {
  localStorage.removeItem("nexusiq_session");
  location.href = "/";
}

const isActive = (pathname: string, href: string) =>
  href === "/" ? pathname === "/" : pathname.startsWith(href);

const isDev = process.env.NODE_ENV !== "production";
// Hover-də səhifə datasını qabaqcadan çəkənlər (skeleton-suz açılış).
const DATA_PREWARM: Record<string, () => void> = {
  "/anomalies": prefetchAnomalies,
};
const _warmed = new Set<string>();

export function AppNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const navRef = useRef<HTMLDivElement>(null);
  useClickOutside(navRef, () => setOpenGroup(null));

  useEffect(() => setOpenGroup(null), [pathname]);

  // Hover/focus — route-u qabaqcadan qızdır: prod prefetch + dev kompilyasiya + data.
  const warm = (href: string) => {
    if (_warmed.has(href)) return;
    _warmed.add(href);
    router.prefetch(href);
    if (isDev) fetch(href, { credentials: "same-origin" }).catch(() => {});
    DATA_PREWARM[href]?.();
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-[var(--header-bg)] backdrop-blur">
      <div className="shell flex h-16 items-center gap-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="text-lg font-semibold tracking-tight">
            Nexus<span className="text-accent">IQ</span>
          </span>
        </Link>

        {/* əsas naviqasiya — düz, alt-xətt göstəricili */}
        <nav ref={navRef} className="hidden h-16 items-stretch md:flex">
          {NAV.map((item) =>
            item.kind === "link" ? (
              <Link
                key={item.href}
                href={item.href}
                onMouseEnter={() => warm(item.href)}
                onFocus={() => warm(item.href)}
                className={`relative flex items-center px-4 text-sm font-medium transition-colors ${
                  isActive(pathname, item.href)
                    ? "text-text"
                    : "text-muted hover:text-text"
                }`}
              >
                {t(item.labelKey)}
                {isActive(pathname, item.href) && (
                  <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-accent" />
                )}
              </Link>
            ) : (
              <div key={item.labelKey} className="relative flex items-stretch">
                <button
                  onClick={() =>
                    setOpenGroup((g) => (g === item.labelKey ? null : item.labelKey))
                  }
                  onMouseEnter={() => item.items.forEach((l) => warm(l.href))}
                  onFocus={() => item.items.forEach((l) => warm(l.href))}
                  className={`relative flex items-center gap-1.5 px-4 text-sm font-medium transition-colors ${
                    item.items.some((l) => isActive(pathname, l.href)) ||
                    openGroup === item.labelKey
                      ? "text-text"
                      : "text-muted hover:text-text"
                  }`}
                >
                  {t(item.labelKey)}
                  <ChevronDown
                    size={13}
                    className={`text-muted transition-transform duration-200 ${
                      openGroup === item.labelKey ? "rotate-180 text-accent" : ""
                    }`}
                  />
                  {item.items.some((l) => isActive(pathname, l.href)) && (
                    <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-accent" />
                  )}
                </button>
                {openGroup === item.labelKey && (
                  <div className="fade-up absolute left-0 top-full z-40 w-56 overflow-hidden rounded-xl border border-border bg-surface p-1.5 shadow-2xl">
                    {item.items.map((l) => {
                      const Icon = l.icon;
                      const active = isActive(pathname, l.href);
                      return (
                        <Link
                          key={l.href}
                          href={l.href}
                          onMouseEnter={() => warm(l.href)}
                          onFocus={() => warm(l.href)}
                          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                            active
                              ? "bg-accent-soft text-accent"
                              : "text-text hover:bg-surface-hover"
                          }`}
                        >
                          <Icon
                            size={16}
                            className={active ? "text-accent" : "text-muted"}
                          />
                          {t(l.labelKey)}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ),
          )}
        </nav>

        {/* sağ alətlər */}
        <div className="ml-auto flex items-center gap-1">
          <NewsSearch />
          <Link
            href="/alerts"
            title={t("nav.alerts")}
            className="flex items-center rounded-lg px-2 py-1.5 text-muted transition-colors duration-200 hover:bg-surface-hover hover:text-accent"
          >
            <Target size={16} />
          </Link>
          <SavedNavLink />
          <NotifyBell />
          <ThemeToggle />
          <span className="mx-1 h-5 w-px bg-border" />
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

      {/* mobil — bütün keçidlər düz sıra, alt-xətt göstəricili */}
      <nav className="no-scrollbar flex items-center gap-1 overflow-x-auto border-t border-border px-3 py-2 md:hidden">
        {ALL_LEAVES.map((l) => {
          const Icon = l.icon;
          const active = isActive(pathname, l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              onMouseEnter={() => warm(l.href)}
              onFocus={() => warm(l.href)}
              className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:text-text"
              }`}
            >
              <Icon size={14} className={active ? "text-accent" : "text-muted"} />
              {t(l.labelKey)}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
