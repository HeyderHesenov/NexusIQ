"use client";

/** Qiymət siqnalları — localStorage qaydaları. Fon yoxlayıcı AlertWatcher-dədir. */
import { useEffect, useState } from "react";

export interface AlertRule {
  id: string;
  key: string; // aktiv açarı
  label: string;
  direction: "above" | "below";
  price: number;
  createdAt: number;
  triggeredAt: number | null;
}

export const KEY = "nexusiq_alerts";
const EVENT = "nexusiq:alerts";

export function readAlerts(): AlertRule[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

function write(list: AlertRule[]) {
  localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event(EVENT));
}

export function addAlert(
  r: Omit<AlertRule, "id" | "createdAt" | "triggeredAt">,
): void {
  const id = `${r.key}-${r.direction}-${r.price}-${readAlerts().length}`;
  write([
    ...readAlerts(),
    { ...r, id, createdAt: Date.now(), triggeredAt: null },
  ]);
}

export function removeAlert(id: string): void {
  write(readAlerts().filter((a) => a.id !== id));
}

export function markTriggered(id: string): void {
  write(
    readAlerts().map((a) =>
      a.id === id ? { ...a, triggeredAt: Date.now() } : a,
    ),
  );
}

export function useAlerts(): AlertRule[] {
  const [list, setList] = useState<AlertRule[]>([]);
  useEffect(() => {
    const sync = () => setList(readAlerts());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return list;
}
