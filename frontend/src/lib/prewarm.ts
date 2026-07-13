"use client";

import type { useRouter } from "next/navigation";

const isDev = process.env.NODE_ENV !== "production";
// Bir route yalnız bir dəfə qızdırılır — hover təkrarı sorğu yaratmasın.
const _warmed = new Set<string>();

type Router = ReturnType<typeof useRouter>;

/**
 * Route-u hover/fokusda qabaqcadan qızdırır ki, klikdə donmasın.
 *
 * Prod: router.prefetch route-un RSC payload + chunk-larını çəkir.
 * Dev: <Link> prefetch söndürülüdür, ona görə əlavə fetch dev serverini bu
 * route-u kompilyasiyaya məcbur edir (cavab atılır). Beləcə keçid isti olur.
 */
export function warmRoute(router: Router, href: string): void {
  if (_warmed.has(href)) return;
  _warmed.add(href);
  router.prefetch(href);
  if (isDev) fetch(href, { credentials: "same-origin" }).catch(() => {});
}
