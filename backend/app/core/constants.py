"""Layihə boyu paylaşılan sabitlər."""
from __future__ import annotations

from enum import StrEnum


class Category(StrEnum):
    """Xəbər kateqoriyaları. Tablar bunlarla filtrlənir."""

    FOREX = "forex"
    US = "us"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"


# UI-də göstərilən adlar
CATEGORY_LABELS: dict[Category, str] = {
    Category.FOREX: "Forex",
    Category.US: "US Markets",
    Category.CRYPTO: "Crypto",
    Category.COMMODITIES: "Commodities",
}

# Aktiv registrinin `atype`-ı → xəbər kateqoriyası. Aktiv səhifəsindəki Yahoo
# xəbərlərinin öz kateqoriyası yoxdur; örtük (GeneratedThumb) üçün buradan gəlir.
ASSET_TYPE_CATEGORY: dict[str, Category] = {
    "forex": Category.FOREX,
    "crypto": Category.CRYPTO,
    "metal": Category.COMMODITIES,
    "commodity": Category.COMMODITIES,
    "industrial": Category.COMMODITIES,
    "stock": Category.US,
    "index": Category.US,
}
