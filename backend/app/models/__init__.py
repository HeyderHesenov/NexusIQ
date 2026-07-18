"""ORM modelləri. Buradan import → Base.metadata bütün cədvəlləri tanıyır."""
from __future__ import annotations

from app.models.ai_budget import AiUsage, SystemFlag
from app.models.auth_session import AuthSession
from app.models.auth_token import EmailVerificationToken, PasswordResetToken
from app.models.category import Category
from app.models.news import News
from app.models.news_asset import NewsAsset
from app.models.push import PushSubscription
from app.models.source import Source
from app.models.user import User, UserIdentity
from app.models.user_data import (
    UserAlert,
    UserBookmark,
    UserHolding,
    UserPrefs,
    UserSavedEvent,
    UserWatchlist,
)

__all__ = [
    "AiUsage",
    "AuthSession",
    "Category",
    "SystemFlag",
    "EmailVerificationToken",
    "News",
    "NewsAsset",
    "PasswordResetToken",
    "PushSubscription",
    "Source",
    "User",
    "UserAlert",
    "UserBookmark",
    "UserHolding",
    "UserIdentity",
    "UserPrefs",
    "UserSavedEvent",
    "UserWatchlist",
]
