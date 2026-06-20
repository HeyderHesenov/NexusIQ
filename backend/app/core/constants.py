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
