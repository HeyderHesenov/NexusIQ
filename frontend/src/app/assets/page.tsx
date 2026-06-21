"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search, Coins } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Sparkline } from "@/components/charts/Sparkline";
import { WatchButton } from "@/components/assets/WatchButton";
import { getAssetsOverview } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssetOverview, AssetType } from "@/types";

const FILTERS: AssetType[] = ["crypto", "index", "forex", "metal", "commodity"];

export default function AssetsPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState<AssetOverview[]>([]);
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [filter, setFilter] = useState<AssetType>("crypto");
  const [q, setQ] = useState("");

  useEffect(() => {
    getAssetsOverview().then((d) => {
      setRows(d);
      setStatus("ready");
    });
  }, []);

  const query = q.trim().toLowerCase();
  const view = useMemo(
    () =>
      rows.filter(
        (r) =>
          r.type === filter &&
          (!query ||
            r.label.toLowerCase().includes(query) ||
            r.key.toLowerCase().includes(query)),
      ),
    [rows, filter, query],
  );

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-6xl px-5 py-8">
        <div className="mb-5 flex items-center gap-2">
          <Coins size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("assets.title")}
          </h1>
        </div>

        {/* filtr + axtarış */}
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-1 rounded-xl border border-border bg-surface p-1">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                  filter === f
                    ? "bg-accent text-black"
                    : "text-muted hover:text-text"
                }`}
              >
                {t(`atype.${f}`)}
              </button>
            ))}
          </div>
          <div className="relative sm:w-64">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("picker.search")}
              className="w-full rounded-xl border border-border bg-surface py-2 pl-9 pr-3 text-sm focus:border-accent focus:outline-none"
            />
          </div>
        </div>

        {/* cədvəl */}
        <div className="overflow-hidden rounded-card border border-border">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-surface text-muted">
              <tr>
                <th className="w-10 px-3 py-3 text-right font-medium">#</th>
                <th className="px-3 py-3 text-left font-medium">{t("assets.name")}</th>
                <th className="px-3 py-3 text-right font-medium">{t("assets.price")}</th>
                <th className="px-3 py-3 text-right font-medium">24s</th>
                <th className="hidden px-3 py-3 text-right font-medium sm:table-cell">
                  7g
                </th>
                <th className="w-12 px-3 py-3" />
              </tr>
            </thead>
            <tbody>
              {status === "loading" &&
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-t border-border">
                    <td colSpan={6} className="px-3 py-3">
                      <div className="h-6 w-full animate-pulse rounded bg-surface-hover" />
                    </td>
                  </tr>
                ))}

              {status === "ready" &&
                view.map((r, i) => (
                  <tr
                    key={r.key}
                    className="group border-t border-border transition-colors hover:bg-surface-hover"
                  >
                    <td className="px-3 py-2.5 text-right font-mono text-xs text-muted">
                      {i + 1}
                    </td>
                    <td className="px-3 py-2.5">
                      <Link
                        href={`/asset/${r.key}`}
                        className="font-medium hover:text-accent"
                      >
                        {r.label}
                      </Link>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">{r.val}</td>
                    <td
                      className={`px-3 py-2.5 text-right font-mono text-xs ${r.up ? "text-up" : "text-down"}`}
                    >
                      {r.chg}
                    </td>
                    <td className="hidden px-3 py-2.5 sm:table-cell">
                      <div className="flex justify-end">
                        <Sparkline values={r.spark} width={104} height={32} />
                      </div>
                    </td>
                    <td className="px-2 py-2.5">
                      <WatchButton assetKey={r.key} />
                    </td>
                  </tr>
                ))}

              {status === "ready" && view.length === 0 && (
                <tr className="border-t border-border">
                  <td colSpan={6} className="px-3 py-10 text-center text-sm text-muted">
                    {t("picker.none")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
