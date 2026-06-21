"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { useI18n } from "@/lib/i18n";

/** Açıq/qaranlıq tema keçidi. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const { t } = useI18n();
  const dark = theme === "dark";
  return (
    <button
      onClick={toggle}
      title={dark ? t("theme.light") : t("theme.dark")}
      aria-label={dark ? t("theme.light") : t("theme.dark")}
      className="flex items-center rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted transition-all duration-200 hover:border-accent hover:text-accent"
    >
      {dark ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}
