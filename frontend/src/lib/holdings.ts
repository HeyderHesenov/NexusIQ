"use client";

/**
 * Portfel — localStorage-da mövqelər (hesab yoxdur, demo auth). Açar → {qty, avgCost}.
 * Server heç nə saxlamır; /portfel bunları göndərib P&L + pul-çəkili xəbər alır.
 * Dəyişiklikdə "nexusiq:holdings" event-i yayılır → UI canlı yenilənir.
 */
import { useEffect, useState } from "react";
import { isWatched, toggleWatch } from "@/lib/watchlist";

const KEY = "nexusiq_holdings";
const EVENT = "nexusiq:holdings";

export interface Holding {
  qty: number;
  avgCost: number;
  addedAt: number;
}
export interface HoldingRow extends Holding {
  key: string;
}

function read(): Record<string, Holding> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function write(map: Record<string, Holding>) {
  localStorage.setItem(KEY, JSON.stringify(map));
  window.dispatchEvent(new Event(EVENT));
}

/** Yeni mövqe (varsa toxunma). Portfelə əlavə edilən aktiv izlənilənlərə də düşür. */
export function addHolding(key: string): void {
  const map = read();
  if (!map[key]) {
    map[key] = { qty: 1, avgCost: 0, addedAt: Date.now() };
    write(map);
  }
  if (!isWatched(key)) toggleWatch(key);
}

export function updateHolding(key: string, patch: Partial<Holding>): void {
  const map = read();
  if (!map[key]) return;
  map[key] = { ...map[key], ...patch };
  write(map);
}

export function removeHolding(key: string): void {
  const map = read();
  if (map[key]) {
    delete map[key];
    write(map);
  }
}

export function isHeld(key: string): boolean {
  return key in read();
}

export function listHoldings(): HoldingRow[] {
  return Object.entries(read())
    .map(([key, h]) => ({ key, ...h }))
    .sort((a, b) => b.addedAt - a.addedAt);
}

export function useHoldings(): HoldingRow[] {
  const [rows, setRows] = useState<HoldingRow[]>([]);
  useEffect(() => {
    const sync = () => setRows(listHoldings());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return rows;
}
