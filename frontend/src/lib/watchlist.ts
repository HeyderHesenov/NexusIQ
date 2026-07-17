"use client";

/** İzləmə siyahısı — localStorage-da aktiv açarları. */
import { useEffect, useState } from "react";

export const KEY = "nexusiq_watchlist";
const EVENT = "nexusiq:watchlist";
const DEFAULTS = ["btc", "eth", "spx", "ndx", "gold"];

function read(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (raw === null) return [...DEFAULTS];
    return JSON.parse(raw);
  } catch {
    return [...DEFAULTS];
  }
}

function write(keys: string[]) {
  localStorage.setItem(KEY, JSON.stringify(keys));
  window.dispatchEvent(new Event(EVENT));
}

export function isWatched(key: string): boolean {
  return read().includes(key);
}

export function toggleWatch(key: string): boolean {
  const list = read();
  let added: boolean;
  if (list.includes(key)) {
    write(list.filter((k) => k !== key));
    added = false;
  } else {
    write([...list, key]);
    added = true;
  }
  return added;
}

export function useWatchlist(): string[] {
  const [keys, setKeys] = useState<string[]>([]);
  useEffect(() => {
    const sync = () => setKeys(read());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return keys;
}

export function useWatched(key: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const sync = () => setOn(isWatched(key));
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [key]);
  return on;
}
