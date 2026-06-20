"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Ticker } from "@/components/market/Ticker";
import { useI18n } from "@/lib/i18n";
import type { Category } from "@/types";

const TITLES: Record<Category, string> = {
  forex: "Forex",
  us: "US Markets",
  crypto: "Crypto",
};

export default function HomePage() {
  const { t } = useI18n();
  const [active, setActive] = useState<Category>("forex");

  function logout() {
    localStorage.removeItem("nexusfx_session");
    location.reload();
  }

  return (
    <div className="min-h-screen">
      <Header active={active} onChange={setActive} onLogout={logout} />
      <Ticker />

      <main className="mx-auto max-w-7xl px-5 py-8">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
              {TITLES[active]}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {t("home.marketNews")}
            </h1>
          </div>
        </div>

        {/* Xəbərlər yüklənmə vəziyyəti — data analitika addımında qoşulacaq */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <NewsCardSkeleton key={i} />
          ))}
        </div>
      </main>
    </div>
  );
}

/** Xəbər kartının yüklənmə skeleti (shimmer). */
function NewsCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-card border border-border bg-surface">
      <div className="h-40 animate-pulse bg-surface-hover" />
      <div className="space-y-3 p-4">
        <div className="h-3 w-20 animate-pulse rounded bg-surface-hover" />
        <div className="h-4 w-full animate-pulse rounded bg-surface-hover" />
        <div className="h-4 w-4/5 animate-pulse rounded bg-surface-hover" />
        <div className="h-3 w-1/3 animate-pulse rounded bg-surface-hover" />
      </div>
    </div>
  );
}
