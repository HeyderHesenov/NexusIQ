"use client";

import { useEffect, useState } from "react";
import { Bell, BellOff, BellRing } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import {
  currentSubscription,
  disablePush,
  enablePush,
  permissionState,
  pushSupported,
  sendTestPush,
} from "@/lib/push";

type State = "off" | "on" | "blocked" | "unsupported";

export function NotifyBell() {
  const { t, lang } = useI18n();
  const [state, setState] = useState<State>("off");
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  useEffect(() => {
    if (!pushSupported()) {
      setState("unsupported");
      return;
    }
    if (permissionState() === "denied") {
      setState("blocked");
      return;
    }
    currentSubscription().then((sub) => setState(sub ? "on" : "off"));
  }, []);

  function toast(msg: string) {
    setFlash(msg);
    window.setTimeout(() => setFlash(null), 2600);
  }

  async function toggle() {
    if (busy || state === "unsupported" || state === "blocked") return;
    setBusy(true);
    try {
      if (state === "on") {
        await disablePush();
        setState("off");
        toast(t("notify.off"));
      } else {
        const ok = await enablePush(lang);
        if (ok) {
          setState("on");
          toast(t("notify.on"));
          await sendTestPush();
        } else {
          setState(permissionState() === "denied" ? "blocked" : "off");
        }
      }
    } finally {
      setBusy(false);
    }
  }

  const title =
    state === "on"
      ? t("notify.enabled")
      : state === "blocked"
        ? t("notify.blocked")
        : state === "unsupported"
          ? t("notify.unsupported")
          : t("notify.enable");

  const Icon = state === "on" ? BellRing : state === "blocked" ? BellOff : Bell;
  const disabled = busy || state === "unsupported" || state === "blocked";

  return (
    <div className="relative">
      <button
        onClick={toggle}
        disabled={disabled}
        title={title}
        aria-label={title}
        className={`flex items-center rounded-lg border px-3 py-1.5 text-sm transition-all duration-200 ${
          state === "on"
            ? "border-accent/60 bg-accent/10 text-accent"
            : "border-border bg-surface text-muted hover:text-text hover:bg-surface-hover"
        } ${disabled ? "cursor-not-allowed opacity-50" : ""} ${busy ? "animate-pulse" : ""}`}
      >
        <Icon size={15} />
      </button>

      {flash && (
        <div className="absolute right-0 top-full z-40 mt-2 whitespace-nowrap rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text shadow-lg">
          {flash}
        </div>
      )}
    </div>
  );
}
