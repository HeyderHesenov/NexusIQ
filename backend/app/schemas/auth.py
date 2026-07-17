"""Auth Pydantic sxemləri (camelCase — frontend ilə uyğun).

Parol sahələri geniş sərhədlə (1..256) — əsl siyasət (12/128, NFKC) `security.validate_password`-da,
maşın-oxunan `code` qaytarır. EmailStr email-validator (NFKC/IDNA normalizasiya) tələb edir.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from app.models import User


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RegisterIn(_CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    display_name: str | None = Field(default=None, max_length=80)


class LoginIn(_CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeIn(_CamelModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class ResetRequestIn(_CamelModel):
    email: EmailStr


class ResetConfirmIn(_CamelModel):
    token: str = Field(min_length=1, max_length=512)
    password: str = Field(min_length=1, max_length=256)


class GoogleIn(_CamelModel):
    credential: str = Field(min_length=1, max_length=8192)  # Google ID token (JWT)


class UserOut(_CamelModel):
    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    role: str
    email_verified: bool

    @classmethod
    def of(cls, u: User) -> "UserOut":
        return cls(
            id=str(u.id),
            email=u.email,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            role=u.role,
            email_verified=u.email_verified_at is not None,
        )


class OkOut(_CamelModel):
    ok: bool = True
