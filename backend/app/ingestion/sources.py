"""RSS mənbələrinin reyestri. Hər feed bir kateqoriyaya bağlıdır.

Tab filtri (Forex / US / Crypto) məhz bu kateqoriya ilə işləyir —
mənbə hansı kateqoriyadırsa, xəbər də o kateqoriyaya düşür.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import Category


@dataclass(frozen=True)
class FeedSource:
    """Bir RSS mənbəyi."""

    name: str          # Source.name (unikal)
    rss_url: str       # feed ünvanı
    category: Category
    homepage: str | None = None


# Sınaqdan keçmiş, açıq RSS feed-ləri.
FEEDS: list[FeedSource] = [
    # ---- Forex ----
    FeedSource("FXStreet", "https://www.fxstreet.com/rss/news",
               Category.FOREX, "https://www.fxstreet.com"),
    FeedSource("ForexLive", "https://www.forexlive.com/feed/news",
               Category.FOREX, "https://www.forexlive.com"),
    FeedSource("DailyFX", "https://www.dailyfx.com/feeds/market-news",
               Category.FOREX, "https://www.dailyfx.com"),

    # ---- US Markets ----
    # HTTPS məcburidir: plain HTTP + `follow_redirects=True` (rss_collector) on-path
    # hücumçuya feed-ə istənilən `media:content` URL-i yeritməyə imkan verirdi. O
    # URL sonra DB-yə düşür və `/img/news/{id}` proksisi onu SERVER tərəfdə çəkir
    # → "attacker-adjacent" data "attacker-controlled"-a çevrilirdi.
    FeedSource("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/",
               Category.US, "https://www.marketwatch.com"),
    FeedSource("CNBC Markets",
               "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135",
               Category.US, "https://www.cnbc.com"),
    FeedSource("Yahoo Finance", "https://finance.yahoo.com/news/rssindex",
               Category.US, "https://finance.yahoo.com"),

    # ---- Crypto ----
    FeedSource("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/",
               Category.CRYPTO, "https://www.coindesk.com"),
    FeedSource("Cointelegraph", "https://cointelegraph.com/rss",
               Category.CRYPTO, "https://cointelegraph.com"),
    FeedSource("Decrypt", "https://decrypt.co/feed",
               Category.CRYPTO, "https://decrypt.co"),

    # ---- Commodities (əmtəə: enerji, uran, taxıl, metal və s.) ----
    FeedSource("OilPrice", "https://oilprice.com/rss/main",
               Category.COMMODITIES, "https://oilprice.com"),
    # `Investing Commodities` şəkil vermir: `i-invdn-com.investing.com` şəkilləri VƏ
    # investing.com məqalə səhifələri real brauzer UA ilə də 403 qaytarır (bot-blok),
    # ona görə həm inline, həm og:image backfill uğursuzdur → kart brendli örtüyə düşür.
    # Feed məzmun üçün saxlanır, amma aşağıdakı şəkilli mənbələr onun payını seyrəldir.
    # (Yeni mənbə əlavə edəndə: HTTPS məcburi + son 10 məqalənin ≥70%-i proksidən
    #  şəkil verməli — bax scripts probe. Bunlar prod UA ilə 90-100% keçdi.)
    FeedSource("Investing Commodities", "https://www.investing.com/rss/news_11.rss",
               Category.COMMODITIES, "https://www.investing.com"),
    FeedSource("Mining.com", "https://www.mining.com/feed/",
               Category.COMMODITIES, "https://www.mining.com"),
    FeedSource("World Oil", "https://www.worldoil.com/rss?feed=news",
               Category.COMMODITIES, "https://www.worldoil.com"),
    FeedSource("Northern Miner", "https://www.northernminer.com/feed/",
               Category.COMMODITIES, "https://www.northernminer.com"),
    FeedSource("Natural Gas Intelligence", "https://www.naturalgasintel.com/feed/",
               Category.COMMODITIES, "https://www.naturalgasintel.com"),
]
