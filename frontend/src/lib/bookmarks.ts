"use client";

/**
 * Bookmark sistemi — serverlə sinxron in-memory store (`/me/bookmarks`).
 * Server yalnız news_id saxlayır; SİYAHI serverdən canlı NewsItem sətirləri kimi
 * gəlir (hydrate). Optimistik yaddaşda isə tam NewsItem snapshot-u saxlanır ki,
 * /saved səhifəsi sync gözləmədən dərhal göstərsin.
 *
 * `toggleBookmark` sinxron `boolean` qaytarır; dəyişiklikdə "nexusiq:bookmarks"
 * event-i yayılır.
 */
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { NewsItem } from "@/types";

export const KEY = "nexusiq_bookmarks";
const EVENT = "nexusiq:bookmarks";

let store: Record<string, NewsItem> = {};

function emit(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENT));
}

export async function hydrate(): Promise<void> {
  try {
    const rows = await apiGet<NewsItem[]>("/me/bookmarks");
    const map: Record<string, NewsItem> = {};
    for (const n of rows) map[String(n.id)] = n;
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

function withoutId(id: string): Record<string, NewsItem> {
  const rest = { ...store };
  delete rest[id];
  return rest;
}

async function syncBookmark(
  newsId: number,
  added: boolean,
  item: NewsItem,
): Promise<void> {
  try {
    if (added) await apiPost(`/me/bookmarks/${newsId}`, {});
    else await apiDelete(`/me/bookmarks/${newsId}`);
  } catch {
    // Geri qaytar.
    if (added) store = withoutId(item.id);
    else store = { ...store, [item.id]: item };
    emit();
  }
}

export function isBookmarked(id: string): boolean {
  return id in store;
}

export function toggleBookmark(item: NewsItem): boolean {
  const added = !store[item.id];
  store = added ? { ...store, [item.id]: item } : withoutId(item.id);
  emit();
  // Server news_id (int) ilə işləyir; qeyri-rəqəmsal id-lər yalnız lokal qalır.
  const nid = Number(item.id);
  if (Number.isFinite(nid)) void syncBookmark(nid, added, item);
  return added;
}

export function listBookmarks(): NewsItem[] {
  return Object.values(store).sort((a, b) =>
    (b.publishedAt || "").localeCompare(a.publishedAt || ""),
  );
}

/** Bir xəbərin bookmark vəziyyətini canlı izləyən hook. */
export function useBookmark(id: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const sync = () => setOn(isBookmarked(id));
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, [id]);
  return on;
}

/** Bütün bookmark siyahısını canlı izləyən hook (/saved üçün). */
export function useBookmarkList(): NewsItem[] {
  const [items, setItems] = useState<NewsItem[]>([]);
  useEffect(() => {
    const sync = () => setItems(listBookmarks());
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  return items;
}
