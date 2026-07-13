"use client";

import { memo, useEffect, useRef, useState } from "react";
import { Sparkles, X, ArrowUp } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { streamChat } from "@/lib/api";
import { PairChart } from "@/components/correlation/PairChart";
import type { CorrPair } from "@/types";

type Msg = { role: "user" | "assistant"; text: string; chart?: CorrPair };

/**
 * Sağ-altda üzən AI Analitik düyməsi + sağ drawer (ABB bankı tərzi).
 * Arxa fonda iki AI debate edir; istifadəçiyə tək cavab gəlir.
 */
export function AIAssistantFab() {
  const { t, lang } = useI18n();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, busy]);

  function patchLast(fn: (m: Msg) => Msg) {
    setMessages((msgs) => {
      const copy = [...msgs];
      copy[copy.length - 1] = fn(copy[copy.length - 1]);
      return copy;
    });
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    // istifadəçi sualı + boş köməkçi mesajı (axın bura yazılacaq)
    setMessages((m) => [
      ...m,
      { role: "user", text: q },
      { role: "assistant", text: "" },
    ]);
    setBusy(true);
    try {
      await streamChat(q, lang, {
        onChart: (chart) => patchLast((m) => ({ ...m, chart })),
        onDelta: (delta) => patchLast((m) => ({ ...m, text: m.text + delta })),
      });
    } catch {
      patchLast((m) => ({ ...m, text: m.text || t("ai.error") }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={t("ai.title")}
        aria-label={t("ai.title")}
        className="group fixed bottom-6 right-6 z-40 grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-accent to-amber-500 text-black shadow-lg shadow-accent/25 transition-transform duration-200 ease-out hover:scale-105 active:scale-95"
      >
        <span className="pointer-events-none absolute inset-0 animate-ping rounded-full bg-accent/40 [animation-duration:2.4s]" />
        <Sparkles size={22} className="relative" />
      </button>

      <div
        className={`fixed inset-0 z-50 overflow-hidden ${open ? "" : "pointer-events-none"}`}
        aria-hidden={!open}
      >
        <div
          onClick={() => setOpen(false)}
          className={`absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity duration-300 ${
            open ? "opacity-100" : "opacity-0"
          }`}
        />

        <aside
          className={`absolute right-0 top-0 flex h-full w-[min(100vw,420px)] flex-col border-l border-border bg-surface shadow-2xl transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
            open ? "translate-x-0" : "translate-x-full"
          }`}
          role="dialog"
          aria-label={t("ai.title")}
        >
          <header className="flex items-center justify-between border-b border-border px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-accent to-amber-500 text-black">
                <Sparkles size={18} />
              </span>
              <div className="leading-tight">
                <p className="text-sm font-semibold">{t("ai.title")}</p>
                <p className="font-mono text-[11px] text-muted">{t("ai.tag")}</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="grid h-8 w-8 place-items-center rounded-lg text-muted transition-colors hover:bg-surface-hover hover:text-text"
              aria-label={t("ai.close")}
            >
              <X size={18} />
            </button>
          </header>

          {/* söhbət axını */}
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-6">
            {/* salamlama */}
            <Bubble role="assistant">{t("ai.greeting")}</Bubble>

            {/* boş halda nümunə suallar */}
            {messages.length === 0 && !busy && (
              <div className="space-y-2 pt-1">
                <p className="px-1 font-mono text-[11px] uppercase tracking-wider text-muted">
                  {t("ai.tryLabel")}
                </p>
                {["ai.ex1", "ai.ex2", "ai.ex3"].map((k) => (
                  <button
                    key={k}
                    onClick={() => send(t(k))}
                    className="w-full rounded-xl border border-border bg-bg px-4 py-2.5 text-left text-sm text-muted transition-colors hover:border-accent/50 hover:text-text"
                  >
                    {t(k)}
                  </button>
                ))}
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className="space-y-2">
                {m.role === "assistant" && m.chart && (
                  <ChatChart pair={m.chart} />
                )}
                {(m.text || m.role === "user") && (
                  <Bubble role={m.role}>{m.text}</Bubble>
                )}
              </div>
            ))}

            {busy &&
              (() => {
                const last = messages[messages.length - 1];
                const waiting =
                  last?.role === "assistant" && !last.text && !last.chart;
                return waiting ? <Thinking label={t("ai.thinking")} /> : null;
              })()}
          </div>

          {/* giriş sahəsi */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2 border-t border-border p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
              placeholder={t("ai.placeholder")}
              className="flex-1 rounded-xl border border-border bg-bg px-4 py-3 text-sm text-text placeholder:text-muted/70 focus:border-accent focus:outline-none disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-black transition-opacity hover:brightness-110 disabled:opacity-40"
              aria-label={t("ai.send")}
            >
              <ArrowUp size={18} />
            </button>
          </form>
        </aside>
      </div>
    </>
  );
}

/** AI cavabı ilə birlikdə gələn korrelyasiya qrafiki kartı.
 *
 * memo: axın zamanı hər token setMessages tetikləyir; `pair` dəyişməyibsə
 * PairChart (bahalı SVG) yenidən render olunmasın. */
const ChatChart = memo(function ChatChart({ pair }: { pair: CorrPair }) {
  const v = pair.value;
  const color = v >= 0.1 ? "text-up" : v <= -0.1 ? "text-down" : "text-muted";
  return (
    <div className="rounded-2xl rounded-tl-sm border border-border bg-surface-hover p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-xs font-semibold">
          {pair.a.label} · {pair.b.label}
        </span>
        <span className={`font-mono text-sm font-semibold ${color}`}>
          {v >= 0 ? "+" : ""}
          {v.toFixed(2)}
        </span>
      </div>
      <PairChart
        series={pair.series}
        labelA={pair.a.label}
        labelB={pair.b.label}
        compact
      />
    </div>
  );
});

/** Söhbət baloncuğu — istifadəçi sağda, AI solda. **bold** dəstəklənir.
 *
 * memo: axın yalnız SON mesajı dəyişir; əvvəlki baloncuqların `children` (mətn)
 * referansı sabit qalır → renderRich təkrar işləməsin. */
const Bubble = memo(function Bubble({
  role,
  children,
}: {
  role: "user" | "assistant";
  children: string;
}) {
  const isUser = role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={`max-w-[88%] space-y-1.5 rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "rounded-tr-sm bg-accent text-black"
            : "rounded-tl-sm bg-surface-hover text-text"
        }`}
      >
        {renderRich(children)}
      </div>
    </div>
  );
});

/** Sətir-sətir: ## başlıqlar, --- ayırıcı, **qalın** mətn. */
function renderRich(text: string) {
  const lines = text.split("\n");
  const out: React.ReactNode[] = [];
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed === "---") return; // boş/ayırıcı sətirləri at
    const heading = trimmed.match(/^#{1,6}\s+(.*)$/);
    if (heading) {
      out.push(
        <p key={i} className="pt-1 text-[13px] font-semibold text-accent">
          {heading[1]}
        </p>,
      );
      return;
    }
    out.push(<p key={i}>{bold(trimmed)}</p>);
  });
  return out;
}

/** **qalın** seqmentləri render edir. */
function bold(line: string) {
  return line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

/** "Düşünür…" göstəricisi (debate gözlənilərkən). */
function Thinking({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 px-1 text-sm text-muted">
      <span className="flex gap-1">
        <Dot d="0ms" />
        <Dot d="150ms" />
        <Dot d="300ms" />
      </span>
      {label}
    </div>
  );
}

function Dot({ d }: { d: string }) {
  return (
    <span
      className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent"
      style={{ animationDelay: d }}
    />
  );
}
