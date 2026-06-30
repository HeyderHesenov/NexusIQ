"use client";

import { useState } from "react";
import { GeneratedThumb } from "@/components/news/GeneratedThumb";
import type { Category } from "@/types";

/**
 * Real xəbər şəkli — mənbənin og:image-i (naşirin paylaşım üçün verdiyi).
 * Şəkil yoxdur və ya yüklənmirsə brendli generativ thumbnail-a düşür.
 */
export function NewsImage({
  src,
  seed,
  category,
  className,
}: {
  src: string | null;
  seed: string;
  category: Category;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <GeneratedThumb seed={seed} category={category} className={className} />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      loading="lazy"
      className={`object-cover ${className ?? ""}`}
      onError={() => setFailed(true)}
    />
  );
}
