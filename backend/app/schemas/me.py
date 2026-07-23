"""/me/* per-user data sxemləri (camelCase). Decimal (Float YOX) + allow_inf_nan=False
+ href validasiyası — server-side stored open-redirect / inf/NaN qorusu."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

_KEY_RE = r"^[a-z0-9_.\-=^]{1,32}$"
_MAX = Decimal("1e12")


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HoldingIn(_Camel):
    qty: Decimal = Field(gt=0, le=_MAX, max_digits=24, decimal_places=8, allow_inf_nan=False)
    avg_cost: Decimal | None = Field(
        default=None, ge=0, le=_MAX, max_digits=24, decimal_places=8, allow_inf_nan=False
    )


class HoldingOut(_Camel):
    key: str
    qty: Decimal
    avg_cost: Decimal | None = None


class AlertIn(_Camel):
    asset_key: str = Field(pattern=_KEY_RE)
    label: str | None = Field(default=None, max_length=64)
    direction: Literal["above", "below"]
    price: Decimal = Field(gt=0, le=_MAX, max_digits=24, decimal_places=8, allow_inf_nan=False)


class AlertOut(_Camel):
    id: str
    asset_key: str
    label: str | None
    direction: str
    price: Decimal
    active: bool
    triggered_at: str | None = None


class SavedEventPayload(_Camel):
    """Klient-təchizatlı, sonradan render olunur → şəkilli validasiya, href sərt."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    title: str | None = Field(default=None, max_length=300)
    href: str = Field(max_length=1000)
    country: str | None = Field(default=None, max_length=8)
    impact: str | None = Field(default=None, max_length=16)
    date: str | None = Field(default=None, max_length=40)

    @field_validator("href")
    @classmethod
    def _href_internal(cls, v: str) -> str:
        # Daxili yol olmalı: '/' ilə başlamalı, '//' (protocol-relative) OLMAMALI.
        if not v.startswith("/") or v.startswith("//"):
            raise ValueError("href sayt daxili yol olmalıdır")
        return v


class SavedEventIn(_Camel):
    event_key: str = Field(min_length=1, max_length=128)
    payload: SavedEventPayload


class SavedEventOut(_Camel):
    event_key: str
    payload: dict
    saved_at: str | None = None


class PrefsIn(_Camel):
    last_seen: int | None = Field(default=None, ge=0, le=4_102_444_800_000)  # epoch ms
    lang: str | None = Field(default=None, max_length=5)
    theme: str | None = Field(default=None, max_length=5)


class PrefsOut(_Camel):
    last_seen_at: str | None = None
    lang: str = "az"
    theme: str | None = None


# ---- Import (additiv birləşmə) ----

class ImportIn(_Camel):
    watchlist: list[str] = Field(default_factory=list, max_length=500)
    holdings: list[dict] = Field(default_factory=list, max_length=500)
    bookmarks: list[int] = Field(default_factory=list, max_length=2000)
    alerts: list[dict] = Field(default_factory=list, max_length=500)
    saved_events: list[dict] = Field(default_factory=list, max_length=500)


class ImportOut(_Camel):
    imported: int
    skipped: int


class AuditOut(_Camel):
    id: str
    event: str
    ip: str | None = None
    user_agent: str | None = None
    meta: dict | None = None
    created_at: str | None = None


class OkOut(_Camel):
    ok: bool = True
