"use client";

/**
 * Saxlanan bazar təqvim hadisələri — localStorage əsaslı (xəbər bookmark-ları ilə
 * eyni naxış, [[bookmarks.ts]] güzgüsü). Tam SavedEvent snapshot-u saxlanır ki,
 * /saved səhifəsi backend olmadan işləsin. Dəyişiklikdə "nexusiq:saved-events"
 * event-i yayılır → UI canlı yenilənir.
 */
import { useEffect, useState } from "react";
import type { SavedEvent } from "@/types";

const KEY = "nexusiq_saved_events";
const EVENT = "nexusiq:saved-events";

function read(): Record<string, SavedEvent> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function write(map: Record<string, SavedEvent>) {
  localStorage.setItem(KEY, JSON.stringify(map));
  window.dispatchEvent(new Event(EVENT));
}

export function isSavedEvent(id: string): boolean {
  return id in read();
}

export function toggleSavedEvent(item: Omit<SavedEvent, "savedAt">): boolean {
  const map = read();
  let added: boolean;
  if (map[item.id]) {
    delete map[item.id];
    added = false;
  } else {
    map[item.id] = { ...item, savedAt: Date.now() };
    added = true;
  }
  write(map);
  return added;
}

export function listSavedEvents(): SavedEvent[] {
  return Object.values(read()).sort((a, b) => b.savedAt - a.savedAt);
}

/** Bir hadisənin saxlanma vəziyyətini canlı izləyən hook. */
export function useSavedEvent(id: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const sync = () => setOn(isSavedEvent(id));
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [id]);
  return on;
}

/** Bütün saxlanan hadisələri canlı izləyən hook (/saved üçün). */
export function useSavedEventList(): SavedEvent[] {
  const [items, setItems] = useState<SavedEvent[]>([]);
  useEffect(() => {
    const sync = () => setItems(listSavedEvents());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return items;
}
