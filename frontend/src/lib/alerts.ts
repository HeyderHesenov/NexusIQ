"use client";

/**
 * Qiymət siqnalları — serverlə sinxron in-memory store (`/me/alerts`).
 * Fon yoxlayıcı AlertWatcher-dədir. `markTriggered` yalnız lokaldır (server-də
 * "triggered" endpoint-i yoxdur) — cari sessiyada təkrar atəşin qarşısını alır.
 *
 * Public API sinxrondur; dəyişiklikdə "nexusiq:alerts" event-i yayılır.
 */
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";

export interface AlertRule {
  id: string;
  key: string; // aktiv açarı
  label: string;
  direction: "above" | "below";
  price: number;
  createdAt: number;
  triggeredAt: number | null;
}

interface AlertApi {
  id: string;
  assetKey: string;
  label: string | null;
  direction: "above" | "below";
  price: number | string;
  active?: boolean;
  triggeredAt?: string | null;
}

export const KEY = "nexusiq_alerts";
const EVENT = "nexusiq:alerts";

let store: AlertRule[] = [];
let tmpSeq = 0;

function emit(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

function fromApi(a: AlertApi): AlertRule {
  return {
    id: a.id,
    key: a.assetKey,
    label: a.label ?? a.assetKey.toUpperCase(),
    direction: a.direction,
    price: Number(a.price) || 0,
    createdAt: Date.now(),
    triggeredAt: a.triggeredAt ? Date.parse(a.triggeredAt) || null : null,
  };
}

export async function hydrate(): Promise<void> {
  try {
    const rows = await apiGet<AlertApi[]>("/me/alerts");
    store = rows.map(fromApi);
    emit();
  } catch {
    /* köhnə store qalır */
  }
}

export function clearStore(): void {
  store = [];
  emit();
}

export function readAlerts(): AlertRule[] {
  return [...store];
}

export function addAlert(
  r: Omit<AlertRule, "id" | "createdAt" | "triggeredAt">,
): void {
  const tempId = `tmp-${r.key}-${r.direction}-${r.price}-${tmpSeq++}`;
  store = [
    ...store,
    { ...r, id: tempId, createdAt: Date.now(), triggeredAt: null },
  ];
  emit();
  void (async () => {
    try {
      const created = await apiPost<AlertApi | { ok: boolean }>("/me/alerts", {
        assetKey: r.key,
        label: r.label,
        direction: r.direction,
        price: r.price,
      });
      if (created && "id" in created) {
        // Müvəqqəti id-ni serverin real qeydi ilə əvəzlə.
        store = store.map((a) => (a.id === tempId ? fromApi(created) : a));
      } else {
        // Dublikat — server yaratmadı; müvəqqətini at (mövcud qeyd saxlanır).
        store = store.filter((a) => a.id !== tempId);
      }
      emit();
    } catch {
      store = store.filter((a) => a.id !== tempId);
      emit();
    }
  })();
}

export function removeAlert(id: string): void {
  const idx = store.findIndex((a) => a.id === id);
  if (idx < 0) return;
  const prev = store[idx];
  store = store.filter((a) => a.id !== id);
  emit();
  // Hələ serverə çatmamış (müvəqqəti) qeydin silinəcək server tərəfi yoxdur.
  if (prev.id.startsWith("tmp-")) return;
  void apiDelete(`/me/alerts/${encodeURIComponent(prev.id)}`).catch(() => {
    const next = [...store];
    next.splice(Math.min(idx, next.length), 0, prev);
    store = next;
    emit();
  });
}

/** Yalnız lokal: cari sessiyada təkrar atəşin qarşısını alır (server endpoint-i yox). */
export function markTriggered(id: string): void {
  store = store.map((a) =>
    a.id === id ? { ...a, triggeredAt: Date.now() } : a,
  );
  emit();
}

export function useAlerts(): AlertRule[] {
  const [list, setList] = useState<AlertRule[]>([]);
  useEffect(() => {
    const sync = () => setList([...store]);
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  return list;
}
