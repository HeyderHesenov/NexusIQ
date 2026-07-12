"use client";

/**
 * Qlobal backend-status zolağı — server əlçatmaz olanda yuxarıda görünür.
 *
 * Niyə var: api.ts-in fərdi funksiyaları xətanı udub boş data qaytarır
 * (səhifə sınmasın), amma bu, ölü backend-i "boş səhifə" kimi göstərirdi.
 * Bu zolaq həmin halı açıq deyir və özü sağalır: hər 5s health yoxlayır,
 * server qayıdanda qısa "bərpa olundu" göstərib səhifəni yeniləyir —
 * boş qalmış bütün siyahılar avtomatik dolur.
 *
 * Rəng semantikası bazar dilindədir: down = qırmızı (bg-down), bərpa = yaşıl (bg-up).
 */
import { useEffect, useRef, useState } from "react";
import { onBackendStatus, pingHealth } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const HEALTH_POLL_MS = 5_000;
const RELOAD_DELAY_MS = 1_200; // istifadəçi "bərpa olundu"nu görsün, sonra yenilə

export function BackendStatusBanner() {
  const { t } = useI18n();
  const [phase, setPhase] = useState<"up" | "down" | "recovering">("up");
  const wasDown = useRef(false);

  useEffect(() => {
    return onBackendStatus((down) => {
      if (down) {
        wasDown.current = true;
        setPhase("down");
      } else if (wasDown.current) {
        setPhase("recovering");
      }
    });
  }, []);

  // Down ikən dövri health yoxlaması — uğur siqnal vasitəsilə "recovering"ə keçirir.
  useEffect(() => {
    if (phase !== "down") return;
    const id = setInterval(() => void pingHealth(), HEALTH_POLL_MS);
    return () => clearInterval(id);
  }, [phase]);

  useEffect(() => {
    if (phase !== "recovering") return;
    const id = setTimeout(() => window.location.reload(), RELOAD_DELAY_MS);
    return () => clearTimeout(id);
  }, [phase]);

  if (phase === "up") return null;
  const down = phase === "down";

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 top-0 z-[100] flex items-center justify-center gap-2.5 border-b border-border bg-surface px-4 py-2 text-[13px] font-medium text-text shadow-[var(--shadow)]"
    >
      <span
        aria-hidden
        className={`h-2 w-2 shrink-0 rounded-full ${
          down ? "bg-down animate-pulse motion-reduce:animate-none" : "bg-up"
        }`}
      />
      {down ? t("status.down") : t("status.up")}
    </div>
  );
}
