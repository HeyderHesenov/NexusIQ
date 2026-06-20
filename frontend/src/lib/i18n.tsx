"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

export type Lang = "az" | "en" | "ru" | "tr";

export const LANGS: { code: Lang; label: string; flag: string }[] = [
  { code: "az", label: "Azərbaycan", flag: "🇦🇿" },
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "ru", label: "Русский", flag: "🇷🇺" },
  { code: "tr", label: "Türkçe", flag: "🇹🇷" },
];

type Dict = Record<string, string>;

const DICT: Record<Lang, Dict> = {
  az: {
    "intro.tagline": "Bazarı oxu. AI ilə qərar ver.",
    "intro.cta": "Daxil olmaq üçün toxun",
    "intro.feat1": "AI Analiz",
    "intro.feat2": "Canlı Xəbər",
    "intro.feat3": "Korrelyasiya",
    "intro.stats": "12,000+ xəbər · 50+ aktiv pair · 24/7 canlı axın",
    "auth.welcome": "Terminala xoş gəldin",
    "auth.subtitle": "Davam etmək üçün Google hesabınla daxil ol.",
    "auth.google": "Google ilə davam et",
    "auth.loading": "Daxil olunur…",
    "auth.demoNote": "Demo rejimi aktivdir · real Gmail üçün Client ID əlavə et.",
    "auth.terms":
      "Davam edərək Xidmət Şərtləri və Məxfilik Siyasətini qəbul edirsən.",
    "auth.error": "Giriş alınmadı. Yenidən cəhd et.",
    "header.aiAnalyst": "AI Analitik",
    "header.logout": "Çıxış",
    "home.marketNews": "Bazar Xəbərləri",
  },
  en: {
    "intro.tagline": "Read the market. Decide with AI.",
    "intro.cta": "Tap to enter",
    "intro.feat1": "AI Analysis",
    "intro.feat2": "Live News",
    "intro.feat3": "Correlation",
    "intro.stats": "12,000+ news · 50+ active pairs · 24/7 live feed",
    "auth.welcome": "Welcome to the terminal",
    "auth.subtitle": "Sign in with your Google account to continue.",
    "auth.google": "Continue with Google",
    "auth.loading": "Signing in…",
    "auth.demoNote": "Demo mode is active · add a Client ID for real Gmail.",
    "auth.terms":
      "By continuing you accept the Terms of Service and Privacy Policy.",
    "auth.error": "Sign-in failed. Please try again.",
    "header.aiAnalyst": "AI Analyst",
    "header.logout": "Log out",
    "home.marketNews": "Market News",
  },
  ru: {
    "intro.tagline": "Читай рынок. Решай с ИИ.",
    "intro.cta": "Нажмите, чтобы войти",
    "intro.feat1": "AI Анализ",
    "intro.feat2": "Живые новости",
    "intro.feat3": "Корреляция",
    "intro.stats": "12 000+ новостей · 50+ активных пар · 24/7 живой поток",
    "auth.welcome": "Добро пожаловать в терминал",
    "auth.subtitle": "Войдите через аккаунт Google, чтобы продолжить.",
    "auth.google": "Продолжить с Google",
    "auth.loading": "Вход…",
    "auth.demoNote":
      "Демо-режим активен · добавьте Client ID для реального Gmail.",
    "auth.terms":
      "Продолжая, вы принимаете Условия использования и Политику конфиденциальности.",
    "auth.error": "Не удалось войти. Попробуйте снова.",
    "header.aiAnalyst": "ИИ Аналитик",
    "header.logout": "Выход",
    "home.marketNews": "Рыночные новости",
  },
  tr: {
    "intro.tagline": "Piyasayı oku. AI ile karar ver.",
    "intro.cta": "Girmek için dokun",
    "intro.feat1": "AI Analiz",
    "intro.feat2": "Canlı Haber",
    "intro.feat3": "Korelasyon",
    "intro.stats": "12.000+ haber · 50+ aktif parite · 24/7 canlı akış",
    "auth.welcome": "Terminale hoş geldin",
    "auth.subtitle": "Devam etmek için Google hesabınla giriş yap.",
    "auth.google": "Google ile devam et",
    "auth.loading": "Giriş yapılıyor…",
    "auth.demoNote": "Demo modu aktif · gerçek Gmail için Client ID ekle.",
    "auth.terms":
      "Devam ederek Hizmet Şartları ve Gizlilik Politikası'nı kabul edersin.",
    "auth.error": "Giriş başarısız. Tekrar dene.",
    "header.aiAnalyst": "AI Analist",
    "header.logout": "Çıkış",
    "home.marketNews": "Piyasa Haberleri",
  },
};

interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
}

const Ctx = createContext<I18nCtx>({
  lang: "az",
  setLang: () => {},
  t: (k) => k,
});

const STORAGE_KEY = "nexusfx_lang";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("az");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Lang | null;
    if (saved && DICT[saved]) setLangState(saved);
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    localStorage.setItem(STORAGE_KEY, l);
  }, []);

  const t = useCallback(
    (key: string) => DICT[lang][key] ?? DICT.az[key] ?? key,
    [lang],
  );

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
