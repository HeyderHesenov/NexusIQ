"use client";

/**
 * Bookmark sistemi — localStorage əsaslı (hesab yoxdur, demo auth).
 * Tam NewsItem snapshot-u saxlanır ki, /saved səhifəsi backend olmadan işləsin.
 * Dəyişiklikdə "nexusiq:bookmarks" event-i yayılır → UI canlı yenilənir.
 */
import { useEffect, useState } from "react";
import type { NewsItem } from "@/types";

export const KEY = "nexusiq_bookmarks";
const EVENT = "nexusiq:bookmarks";

function read(): Record<string, NewsItem> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function write(map: Record<string, NewsItem>) {
  localStorage.setItem(KEY, JSON.stringify(map));
  window.dispatchEvent(new Event(EVENT));
}

export function isBookmarked(id: string): boolean {
  return id in read();
}

export function toggleBookmark(item: NewsItem): boolean {
  const map = read();
  let added: boolean;
  if (map[item.id]) {
    delete map[item.id];
    added = false;
  } else {
    map[item.id] = item;
    added = true;
  }
  write(map);
  return added;
}

export function listBookmarks(): NewsItem[] {
  return Object.values(read()).sort((a, b) =>
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
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
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
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return items;
}
