"use client";

import { useEffect, useState } from "react";
import { Target, Trash2 } from "lucide-react";
import { AppNav } from "@/components/layout/AppNav";
import { Footer } from "@/components/layout/Footer";
import { getAssets } from "@/lib/api";
import { addAlert, removeAlert, useAlerts } from "@/lib/alerts";
import { useI18n } from "@/lib/i18n";
import type { Asset } from "@/types";

export default function AlertsPage() {
  const { t } = useI18n();
  const alerts = useAlerts();
  const [registry, setRegistry] = useState<Asset[]>([]);
  const [key, setKey] = useState("btc");
  const [dir, setDir] = useState<"above" | "below">("above");
  const [price, setPrice] = useState("");

  useEffect(() => {
    getAssets().then(setRegistry);
  }, []);

  function create() {
    const p = parseFloat(price);
    if (!Number.isFinite(p)) return;
    const label = registry.find((a) => a.key === key)?.label ?? key;
    addAlert({ key, label, direction: dir, price: p });
    setPrice("");
  }

  const active = alerts.filter((a) => a.triggeredAt === null);
  const fired = alerts.filter((a) => a.triggeredAt !== null);

  return (
    <div className="flex min-h-screen flex-col">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-5 py-8">
        <div className="mb-2 flex items-center gap-2">
          <Target size={18} className="text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("nav.alerts")}
          </h1>
        </div>
        <p className="mb-5 text-sm text-muted">{t("alert.subtitle")}</p>

        {/* yaratma formu */}
        <section className="rounded-card border border-border bg-surface p-4">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="rounded-lg border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none"
            >
              {registry.map((a) => (
                <option key={a.key} value={a.key}>
                  {a.label}
                </option>
              ))}
            </select>
            <div className="flex gap-1 rounded-lg border border-border bg-bg p-1">
              {(["above", "below"] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDir(d)}
                  className={`rounded-md px-3 py-1 text-sm transition-all ${
                    dir === d ? "bg-accent text-black" : "text-muted hover:text-text"
                  }`}
                >
                  {d === "above" ? t("alert.above") : t("alert.below")}
                </button>
              ))}
            </div>
            <input
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              inputMode="decimal"
              placeholder={t("alert.pricePh")}
              className="w-32 rounded-lg border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
            <button
              onClick={create}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-black transition-opacity hover:brightness-110"
            >
              {t("alert.create")}
            </button>
          </div>
          <p className="mt-2 text-xs text-muted">{t("alert.notifyHint")}</p>
        </section>

        {/* aktiv siqnallar */}
        <section className="mt-6">
          <h2 className="mb-3 text-sm font-semibold">{t("alert.active")}</h2>
          {active.length === 0 ? (
            <p className="rounded-card border border-dashed border-border py-10 text-center text-sm text-muted">
              {t("alert.none")}
            </p>
          ) : (
            <div className="space-y-2">
              {active.map((a) => (
                <Row
                  key={a.id}
                  label={a.label}
                  text={`${a.direction === "above" ? "▲" : "▼"} ${a.price}`}
                  onDelete={() => removeAlert(a.id)}
                />
              ))}
            </div>
          )}
        </section>

        {/* tetiklənmişlər */}
        {fired.length > 0 && (
          <section className="mt-6">
            <h2 className="mb-3 text-sm font-semibold text-muted">
              {t("alert.fired")}
            </h2>
            <div className="space-y-2">
              {fired.map((a) => (
                <Row
                  key={a.id}
                  label={a.label}
                  text={`${a.direction === "above" ? "▲" : "▼"} ${a.price} ✓`}
                  dim
                  onDelete={() => removeAlert(a.id)}
                />
              ))}
            </div>
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
}

function Row({
  label,
  text,
  dim,
  onDelete,
}: {
  label: string;
  text: string;
  dim?: boolean;
  onDelete: () => void;
}) {
  return (
    <div
      className={`flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-2.5 ${dim ? "opacity-60" : ""}`}
    >
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm text-muted">{text}</span>
        <button
          onClick={onDelete}
          className="text-muted transition-colors hover:text-down"
          aria-label="sil"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}
