"use client";

/**
 * Saxlanan bazar təqvim hadisələri — serverlə sinxron in-memory store
 * (`/me/saved-events`). [[bookmarks.ts]] güzgüsü. Server `{eventKey, payload}`
 * saxlayır; klient SavedEvent sahələri payload-a xəritələnir və hydrate-da bərpa
 * olunur. `toggleSavedEvent` sinxron `boolean` qaytarır; dəyişiklikdə
 * "nexusiq:saved-events" event-i yayılır.
 *
 * ID kanonlaşdırma: klient id-ləri (məs. `event:US:...:CPI m/m`) `/`, boşluq və
 * s. saxlaya bilər — bunlar DELETE yol parametrini sındırar. `eventKeyOf` id-ni
 * URL-təhlükəsiz kanona (yalnız `[A-Za-z0-9_.:=^-]`, ≤128) salır; store açarı,
 * axtarış, sinxron VƏ hydrate hamısı eyni kanonu işlədir → uyğunluq qorunur.
 */
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { SavedEvent } from "@/types";

export const KEY = "nexusiq_saved_events";
const EVENT = "nexusiq:saved-events";

interface SavedPayloadApi {
  title?: string | null;
  href: string;
  country?: string | null;
  date?: string | null;
}
interface SavedApi {
  eventKey: string;
  payload: SavedPayloadApi;
  savedAt?: string | null;
}

let store: Record<string, SavedEvent> = {};

function emit(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

/** Klient id → URL-təhlükəsiz kanonik eventKey (idempotent, ≤128). */
export function eventKeyOf(id: string): string {
  return id.replace(/[^A-Za-z0-9_.:=^-]/g, "_").slice(0, 128);
}

// Klient SavedEvent → server payload (sahə uzunluqları backend limitlərinə kəsilir).
function toPayload(item: Omit<SavedEvent, "savedAt">): SavedPayloadApi {
  return {
    title: item.name.slice(0, 300),
    href: item.href,
    country: item.badge ? item.badge.slice(0, 8) : undefined,
    date: item.sub ? item.sub.slice(0, 40) : undefined,
  };
}

function fromApi(s: SavedApi): SavedEvent {
  return {
    id: s.eventKey,
    name: s.payload?.title ?? "",
    badge: s.payload?.country ?? "",
    sub: s.payload?.date ?? "",
    href: s.payload?.href ?? "#",
    savedAt: s.savedAt ? Date.parse(s.savedAt) || Date.now() : Date.now(),
  };
}

export async function hydrate(): Promise<void> {
  try {
    const rows = await apiGet<SavedApi[]>("/me/saved-events");
    const map: Record<string, SavedEvent> = {};
    for (const s of rows) map[s.eventKey] = fromApi(s);
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

function withoutKey(k: string): Record<string, SavedEvent> {
  const rest = { ...store };
  delete rest[k];
  return rest;
}

async function syncSaved(
  item: Omit<SavedEvent, "savedAt">,
  added: boolean,
): Promise<void> {
  const k = eventKeyOf(item.id);
  try {
    if (added) {
      await apiPost("/me/saved-events", { eventKey: k, payload: toPayload(item) });
    } else {
      await apiDelete(`/me/saved-events/${encodeURIComponent(k)}`);
    }
  } catch {
    // Geri qaytar.
    if (added) store = withoutKey(k);
    else if (!store[k]) {
      store = { ...store, [k]: { ...item, savedAt: Date.now() } };
    }
    emit();
  }
}

export function isSavedEvent(id: string): boolean {
  return eventKeyOf(id) in store;
}

export function toggleSavedEvent(item: Omit<SavedEvent, "savedAt">): boolean {
  const k = eventKeyOf(item.id);
  const added = !store[k];
  store = added
    ? { ...store, [k]: { ...item, savedAt: Date.now() } }
    : withoutKey(k);
  emit();
  void syncSaved(item, added);
  return added;
}

export function listSavedEvents(): SavedEvent[] {
  return Object.values(store).sort((a, b) => b.savedAt - a.savedAt);
}

/** Bir hadisənin saxlanma vəziyyətini canlı izləyən hook. */
export function useSavedEvent(id: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const sync = () => setOn(isSavedEvent(id));
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
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
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  return items;
}
