"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Əsas route-ları fonda əvvəlcədən qızdırır ki, keçidlər donmasın.
 *
 * Niyə: Next dev-də <Link> prefetch söndürülüb, ona görə hər ilk klik route-u
 * o anda kompilyasiya edir — URL commit olana qədər səhifə donur (~0.3–1.6s).
 *
 * Prod-da: router.prefetch() route-un RSC payload-unu və chunk-larını ucuz
 * qabaqcadan yükləyir.
 * Dev-də: prefetch kompilyasiya tetikləmir, ona görə əlavə olaraq route-u
 * sadəcə fetch edib dev serverini kompilyasiyaya məcbur edirik (cavab atılır).
 * Beləcə hər keçid isti (~40ms) olur.
 */
const ROUTES = [
  "/",
  "/radar",
  "/assets",
  "/markets",
  "/watchlist",
  "/anomalies",
  "/analogs",
  "/compare",
  "/correlation",
  "/powerlaw",
  "/alerts",
  "/saved",
];

const isDev = process.env.NODE_ENV !== "production";

export function RoutePrewarm() {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    let i = 0;
    let timer: ReturnType<typeof setTimeout>;

    const warmNext = () => {
      if (cancelled || i >= ROUTES.length) return;
      const route = ROUTES[i];
      i += 1;

      router.prefetch(route);
      if (isDev) {
        // dev serverini bu route-u kompilyasiyaya məcbur et; cavabı at.
        fetch(route, { credentials: "same-origin" }).catch(() => {});
      }

      // Növbəti route-u stagger-lə qızdır — serveri eyni anda boğmasın.
      timer = setTimeout(warmNext, 250);
    };

    timer = setTimeout(warmNext, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [router]);

  return null;
}
