"""Naşir "chrome" şəkilləri — sayt loqosu / abunə placeholder-i / generik doldurucu.

Bu URL-lər HTTP 200 və real piksel qaytarır, ona görə `NewsImage`-in
`naturalWidth <= 1` qoruması onları TUTMUR — kartda dartılmış loqo görünür.
Süzülüb `None` edilirlər ki, örtük (GeneratedThumb) onları əvəzləsin.

DAR deny-list — yalnız təsdiqlənmiş sabit URL-lər. Heuristika QADAĞAN:
- Fayl adında "logo" olması meyar DEYİL: naşirlər real məqalə şəkillərini də belə
  adlandırır (decrypt "kalshi-logo-decrypt-style" həmin məqalənin ÖZ sənət işidir).
  `image_url ~* 'logo'` DB-də 14 real şəkil tutur — onlar qalmalıdır.
- Təkrar-istifadə sayı da meyar DEYİL: FXStreet real stock-fotosunu qanuni təkrarlayır.

Süzgəc SERİALİZASİYA qatındadır, ingest-də yox. Səbəb: `enrich_images.backfill`
`image_url IS NULL` seçir və cəhd-izləməsi yoxdur → zibil sətirləri NULL etsək hər
dövr eyni məqalələri yenidən çəkib eyni zibili alardı (daimi retry döngəsi).
Sətirdəki zibil URL "artıq cəhd edilib" markeri rolunu oynayır.
"""
from __future__ import annotations

_JUNK: tuple[str, ...] = (
    "s.yimg.com/uc/fin/img/non-sub-report-thumb",  # Yahoo abunə placeholder-i
    "i-invdn-com.investing.com/news/world_news_",  # Investing generik doldurucu
    "/themes/miningdotcom/images/mdc-site-logo",   # Mining.com sayt loqosu
    "/images/facebook-share-logo.png",             # OilPrice paylaşım loqosu
    # Yahoo MƏQALƏ səhifəsinin og:image-i (yuxarıdakı RSS placeholder-indən FƏRQLİ yol).
    # Backfill zibil sətirləri yenidən skan edəndə bu naxış olmasa 58 sətir düzgün
    # örtükdən → süzgəcdən KEÇƏN dartılmış loqoya çevrilərdi (daha pis). Canlı URL-də
    # `cv/apiv2` İKİ dəfə təkrarlanır → ona yox, sabit quyruğa bağlanırıq.
    "/social/images/yahoo-finance-default-logo",
)


def is_junk_image(url: str | None) -> bool:
    return bool(url) and any(p in url for p in _JUNK)


def clean_image(url: str | None) -> str | None:
    """Zibil örtükləri `None`-a çevirir — qalanına toxunmur."""
    return None if is_junk_image(url) else url
