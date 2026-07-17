"use client";

/**
 * Portfel mövqeləri — serverlə sinxron in-memory store (`/me/holdings`).
 * Açar → {qty, avgCost, addedAt}. `addedAt` yalnız klient sıralaması üçündür
 * (server saxlamır — hydrate sırasından bərpa olunur).
 *
 * Public API sinxrondur: mutasiya = optimistik → `nexusiq:holdings` event-i →
 * fon API (PUT/DELETE) → uğursuzluqda geri qaytar.
 */
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPut } from "@/lib/api";
import { isWatched, toggleWatch } from "@/lib/watchlist";

export const KEY = "nexusiq_holdings";
const EVENT = "nexusiq:holdings";

export interface Holding {
  qty: number;
  avgCost: number;
  addedAt: number;
}
export interface HoldingRow extends Holding {
  key: string;
}

interface HoldingApi {
  key: string;
  qty: number | string;
  avgCost: number | string | null;
}

let store: Record<string, Holding> = {};

function emit(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

export async function hydrate(): Promise<void> {
  try {
    const rows = await apiGet<HoldingApi[]>("/me/holdings");
    const base = Date.now();
    const map: Record<string, Holding> = {};
    rows.forEach((r, i) => {
      map[r.key] = {
        qty: Number(r.qty) || 0,
        avgCost: Number(r.avgCost ?? 0) || 0,
        // Server sırasını qoru: 0-cı element ən böyük addedAt → siyahının başında.
        addedAt: base - i,
      };
    });
    store = map;
    emit();
  } catch {
    /* köhnə store qalır */
  }
}

export function clearStore(): void {
  store = {};
  emit();
}

function withoutKey(key: string): Record<string, Holding> {
  const rest = { ...store };
  delete rest[key];
  return rest;
}

async function syncPut(
  key: string,
  qty: number,
  avgCost: number,
  prev: Holding | undefined,
): Promise<void> {
  try {
    await apiPut(`/me/holdings/${encodeURIComponent(key)}`, { qty, avgCost });
  } catch {
    // Geri qaytar: əvvəl vardısa bərpa et, yeni idisə çıxar.
    if (prev) store = { ...store, [key]: prev };
    else store = withoutKey(key);
    emit();
  }
}

/** Yeni mövqe (varsa toxunma). Portfelə əlavə olunan aktiv izlənilənlərə də düşür. */
export function addHolding(key: string): void {
  if (!store[key]) {
    store = { ...store, [key]: { qty: 1, avgCost: 0, addedAt: Date.now() } };
    emit();
    void syncPut(key, 1, 0, undefined);
  }
  if (!isWatched(key)) toggleWatch(key);
}

export function updateHolding(key: string, patch: Partial<Holding>): void {
  const prev = store[key];
  if (!prev) return;
  const next = { ...prev, ...patch };
  store = { ...store, [key]: next };
  emit();
  // Backend qty>0 tələb edir — boş/sıfır aralıq redaktə vəziyyəti lokal qalır.
  if (next.qty > 0) void syncPut(key, next.qty, next.avgCost, prev);
}

export function removeHolding(key: string): void {
  const prev = store[key];
  if (!prev) return;
  store = withoutKey(key);
  emit();
  void (async () => {
    try {
      await apiDelete(`/me/holdings/${encodeURIComponent(key)}`);
    } catch {
      store = { ...store, [key]: prev };
      emit();
    }
  })();
}

export function isHeld(key: string): boolean {
  return key in store;
}

export function listHoldings(): HoldingRow[] {
  return Object.entries(store)
    .map(([key, h]) => ({ key, ...h }))
    .sort((a, b) => b.addedAt - a.addedAt);
}

export function useHoldings(): HoldingRow[] {
  const [rows, setRows] = useState<HoldingRow[]>([]);
  useEffect(() => {
    const sync = () => setRows(listHoldings());
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  return rows;
}
