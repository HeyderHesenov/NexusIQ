"use client";

/**
 * İzləmə siyahısı — serverlə sinxron in-memory store (`/me/watchlist`).
 *
 * Public API sinxrondur (call site-lar dəyişmir): mutasiya = optimistik yaddaş
 * yeniləməsi → dərhal `nexusiq:watchlist` event-i (ani UI) → fon API çağırışı →
 * uğursuzluqda geri qaytarıb yenidən event yay. `toggleWatch` sinxron `boolean`
 * qaytarır (holdings.addHolding onu inline çağırır).
 */
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";

export const KEY = "nexusiq_watchlist";
const EVENT = "nexusiq:watchlist";

let store: string[] = [];

function emit(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

/** Serverdən yüklə + store-u doldur + event yay. Auth-dan sonra bir dəfə. */
export async function hydrate(): Promise<void> {
  try {
    const d = await apiGet<{ keys: string[] }>("/me/watchlist");
    store = Array.isArray(d?.keys) ? [...d.keys] : [];
    emit();
  } catch {
    /* şəbəkə xətası — köhnə store qalır */
  }
}

/** Çıxışda yaddaşdakı store-u boşalt (əvvəlki istifadəçi sızmasın). */
export function clearStore(): void {
  store = [];
  emit();
}

async function syncWatch(key: string, added: boolean): Promise<void> {
  try {
    if (added) await apiPost(`/me/watchlist/${encodeURIComponent(key)}`, {});
    else await apiDelete(`/me/watchlist/${encodeURIComponent(key)}`);
  } catch {
    // Optimistik dəyişikliyi geri qaytar.
    if (added) store = store.filter((k) => k !== key);
    else if (!store.includes(key)) store = [...store, key];
    emit();
  }
}

export function isWatched(key: string): boolean {
  return store.includes(key);
}

export function toggleWatch(key: string): boolean {
  const added = !store.includes(key);
  store = added ? [...store, key] : store.filter((k) => k !== key);
  emit();
  void syncWatch(key, added);
  return added;
}

export function useWatchlist(): string[] {
  const [keys, setKeys] = useState<string[]>([]);
  useEffect(() => {
    const sync = () => setKeys([...store]);
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  return keys;
}

export function useWatched(key: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const sync = () => setOn(isWatched(key));
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, [key]);
  return on;
}
