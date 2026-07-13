"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkline } from "@/components/charts/Sparkline";
import { WatchButton } from "@/components/assets/WatchButton";
import { warmRoute } from "@/lib/prewarm";
import { useI18n } from "@/lib/i18n";
import type { AssetOverview } from "@/types";

/** CMC cədvəl başlığı — assets və watchlist səhifələrində paylaşılır. */
export function AssetTableHead() {
  const { t } = useI18n();
  return (
    <thead className="border-b border-border bg-surface text-muted">
      <tr>
        <th className="w-10 px-3 py-3 text-right font-medium">#</th>
        <th className="px-3 py-3 text-left font-medium">{t("assets.name")}</th>
        <th className="px-3 py-3 text-right font-medium">{t("assets.price")}</th>
        <th className="px-3 py-3 text-right font-medium">24s</th>
        <th className="hidden px-3 py-3 text-right font-medium sm:table-cell">7g</th>
        <th className="w-12 px-3 py-3" />
      </tr>
    </thead>
  );
}

/** Yüklənmə skeleti — tək sətir. */
export function SkeletonRow() {
  return (
    <tr className="border-t border-border">
      <td colSpan={6} className="px-3 py-3">
        <div className="h-6 w-full animate-pulse rounded bg-surface-hover" />
      </td>
    </tr>
  );
}

/** Bir CMC sətri — rank, ad, qiymət, 24s, sparkline, izlə düyməsi. */
export function AssetRow({
  row,
  rank,
  animClass = "",
}: {
  row: AssetOverview;
  rank: number;
  animClass?: string;
}) {
  const router = useRouter();
  return (
    <tr
      className={`group border-t border-border transition-colors hover:bg-surface-hover ${animClass}`}
    >
      <td className="px-3 py-2.5 text-right font-mono text-xs text-muted">{rank}</td>
      <td className="px-3 py-2.5">
        <Link
          href={`/asset/${row.key}`}
          onMouseEnter={() => warmRoute(router, `/asset/${row.key}`)}
          onFocus={() => warmRoute(router, `/asset/${row.key}`)}
          className="font-medium hover:text-accent"
        >
          {row.label}
        </Link>
      </td>
      <td className="px-3 py-2.5 text-right font-mono">{row.val}</td>
      <td
        className={`px-3 py-2.5 text-right font-mono text-xs ${row.up ? "text-up" : "text-down"}`}
      >
        {row.chg}
      </td>
      <td className="hidden px-3 py-2.5 sm:table-cell">
        <div className="flex justify-end">
          <Sparkline values={row.spark} width={104} height={32} />
        </div>
      </td>
      <td className="px-2 py-2.5">
        <WatchButton assetKey={row.key} />
      </td>
    </tr>
  );
}
