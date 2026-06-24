"use client";

import { useState } from "react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { Ticker } from "@/components/market/Ticker";
import { CategorySelect } from "@/components/news/CategorySelect";
import { MarketCalendar } from "@/components/market/MarketCalendar";
import { FearGreed } from "@/components/market/FearGreed";
import { CATEGORIES } from "@/lib/marketCategories";
import { useI18n } from "@/lib/i18n";
import type { Category } from "@/types";

export default function MarketsPage() {
  const { t } = useI18n();
  const [active, setActive] = useState<Category>("forex");

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <Ticker />

      <main className="mx-auto w-full max-w-7xl px-5 py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
              {t("nav.markets")}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {t("markets.title")}
            </h1>
          </div>
          <CategorySelect active={active} onChange={setActive} />
        </div>

        {active === "crypto" && (
          <div className="mb-6">
            <FearGreed />
          </div>
        )}

        <MarketCalendar key={active} categories={CATEGORIES[active]} />
      </main>

      <Footer />
    </div>
  );
}
