"use client";

import { useEffect, useRef, useState } from "react";
import { GeneratedThumb } from "@/components/news/GeneratedThumb";
import { newsImageUrl } from "@/lib/api";
import type { Category } from "@/types";

/**
 * Xəbər örtüyü — 100% zəmanət: brendli generativ örtük HƏMİŞƏ arxada render
 * olunur, naşirin real og:image-i isə üstündə göstərilir. Şəkil yoxdursa,
 * yüklənmə xətasında, VƏ YA boş/qırıq (naturalWidth ≤ 1: 404-suz boş cavab,
 * 1×1 tracking piksel) yüklənəndə real şəkil gizlənir və örtük görünür —
 * heç vaxt boş/qırıq kart olmur.
 *
 * DİQQƏT: real <img> opacity-gating OLMADAN göstərilir. Əvvəlki versiya (69fc32e)
 * opacity-0→100 fade-in edirdi və keşlənmiş şəkillərdə onLoad yarışını uduzub
 * real şəkli görünməz saxlayırdı (c63f2cb ilə geri qaytarıldı). Burada opacity
 * yoxdur → yarış yoxdur; img ya piksellidir (örtüyü örtür) ya da gizlənir.
 */
export function NewsImage({
  src,
  seed,
  category,
  className,
  compact = false,
  newsId = null,
  width = 640,
}: {
  src: string | null;
  seed: string;
  category: Category;
  className?: string;
  /** Kiçik siyahı örtüyü (96×64) — etiket/wordmark düşür, qlif kiçilir. */
  compact?: boolean;
  /**
   * DB xəbərinin id-si — verilsə şəkil `w` eninə kiçildilmiş proksidən gəlir
   * (naşirin tam ölçülü faylı əvəzinə). Yahoo ehtiyat xəbərlərində id yoxdur;
   * onların şəkli onsuz da 170×128-dir, ona görə birbaşa götürülür.
   */
  newsId?: string | null;
  width?: number;
}) {
  const [failed, setFailed] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  // `src` şəklin MÖVCUDLUĞUNU bildirir (null → örtük); proksi yalnız ünvanı dəyişir.
  const finalSrc = newsId && src ? newsImageUrl(newsId, width) : src;
  const showImg = Boolean(src) && !failed;

  // src dəyişəndə yenidən cəhd; keşlənmiş-qırıq şəkil onLoad atmaya bilər —
  // mount-da `complete` + pikselsizliyi yoxla.
  useEffect(() => {
    setFailed(false);
    const el = imgRef.current;
    if (el?.complete && el.naturalWidth <= 1) setFailed(true);
  }, [finalSrc]);

  return (
    <div className={`relative overflow-hidden ${className ?? ""}`}>
      {/* zəmanətli örtük — həmişə arxada (bg-surface-hover flaşını da örtür) */}
      <div className="absolute inset-0">
        <GeneratedThumb
          seed={seed}
          category={category}
          className="h-full w-full"
          compact={compact}
        />
      </div>

      {/* real şəkil — üstdə, tam görünürlükdə; xəta/boş yüklənmə → gizlənir */}
      {showImg && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          ref={imgRef}
          src={finalSrc as string}
          alt=""
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
          onLoad={(e) => {
            // 200 qaytaran, amma boş/qırıq şəkil onError ATMIR — burada tut.
            if (e.currentTarget.naturalWidth <= 1) setFailed(true);
          }}
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
    </div>
  );
}
