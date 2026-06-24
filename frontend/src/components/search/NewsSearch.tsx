"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Search, X, CornerDownLeft } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { searchNews } from "@/lib/api";
import { localizedNews } from "@/lib/utils";
import type { NewsItem } from "@/types";

/** Header-dəki axtarış tetikləyicisi + ⌘K command-palette overlay. */
export function NewsSearch() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);

  // ⌘K / Ctrl+K ilə aç.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      {/* tetikləyici — kompakt ghost ikon (⌘K hələ də işləyir) */}
      <button
        onClick={() => setOpen(true)}
        title={`${t("search.trigger")} (⌘K)`}
        aria-label={t("search.trigger")}
        className="grid h-9 w-9 place-items-center rounded-lg text-muted transition-colors duration-200 hover:bg-surface-hover hover:text-text"
      >
        <Search size={16} />
      </button>

      {open && <SearchOverlay onClose={() => setOpen(false)} />}
    </>
  );
}

function SearchOverlay({ onClose }: { onClose: () => void }) {
  const { t, lang } = useI18n();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Açılışda fokus + Esc ilə bağla.
  useEffect(() => {
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  // Debounced axtarış.
  useEffect(() => {
    const query = q.trim();
    if (!query) {
      setResults([]);
      setTouched(false);
      return;
    }
    setLoading(true);
    setTouched(true);
    const id = setTimeout(async () => {
      setResults(await searchNews(query));
      setLoading(false);
    }, 300);
    return () => clearTimeout(id);
  }, [q]);

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[12vh]">
      {/* arxa qaraltma */}
      <div
        onClick={onClose}
        className="absolute inset-0 bg-black/55 backdrop-blur-sm fade-up"
        style={{ animationDuration: "0.15s" }}
      />

      {/* axtarış paneli */}
      <div className="ai-panel-in relative w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl">
        {/* giriş sətri */}
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search size={18} className="shrink-0 text-muted" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("search.placeholder")}
            className="w-full bg-transparent py-4 text-[15px] text-text placeholder:text-muted/70 focus:outline-none"
          />
          <button
            onClick={onClose}
            className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-muted transition-colors hover:bg-surface-hover hover:text-text"
            aria-label={t("search.close")}
          >
            <X size={16} />
          </button>
        </div>

        {/* nəticələr */}
        <div className="max-h-[52vh] overflow-y-auto">
          {!touched && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              {t("search.hint")}
            </p>
          )}

          {touched && loading && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              {t("search.loading")}
            </p>
          )}

          {touched && !loading && results.length === 0 && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              {t("search.empty")}
            </p>
          )}

          {results.map((n) => (
            <Link
              key={n.id}
              href={`/news/${n.id}`}
              onClick={onClose}
              className="flex items-start gap-3 border-t border-border px-4 py-3 transition-colors hover:bg-surface-hover"
            >
              <span className="mt-0.5 rounded-md bg-accent/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-accent">
                {n.category}
              </span>
              <span className="flex-1 text-sm text-text">
                {localizedNews(n, lang).title}
              </span>
              <CornerDownLeft size={14} className="mt-1 shrink-0 text-muted" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
