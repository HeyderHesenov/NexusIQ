"""ORM modelləri. Buradan import → Base.metadata bütün cədvəlləri tanıyır."""
from __future__ import annotations

from app.models.category import Category
from app.models.news import News
from app.models.push import PushSubscription
from app.models.source import Source

__all__ = ["Category", "News", "PushSubscription", "Source"]
