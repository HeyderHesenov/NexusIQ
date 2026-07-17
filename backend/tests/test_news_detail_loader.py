"""`/news/{id}` sorğusu qurula bilməlidir — defer+undefer konflikti olmasın.

Kök səbəb (CANLI 500, istifadəçiyə görünən): `_BASE` `defer(News.content)`
daşıyırdı, `get_news` isə üstünə `undefer(News.content)` əlavə edirdi.
SQLAlchemy 2.0 eyni yol üçün bu birləşməni

    InvalidRequestError: Loader strategies for ORM Path[News.content] conflict

sayır → sorğu QURULA BİLMİR → tutulmamış 500. Yəni xəbər detalı səhifəsi
`defer(News.content)`-in `_BASE`-ə əlavə olunduğu commit-dən (e282fb1, əvvəlki
təhlükəsizlik/perf passı) bəri HƏR istifadəçi üçün tam sınıq idi.

Niyə gec tapıldı: brauzerdə bu CORS xətası kimi görünürdü —
"No 'Access-Control-Allow-Origin' header is present". Səbəb: Starlette-də
tutulmamış istisna ən xarici `ServerErrorMiddleware`-də 500-ə çevrilir və
`CORSMiddleware`-i YAN KEÇİR, yəni 500 cavabına CORS başlıqları düşmür. Brauzer
də əsl 500-ü CORS problemi kimi bildirir. Diaqnostika dərsi: API-dən gələn
gözlənilməz CORS xətasını ƏVVƏLCƏ 500 kimi yoxla.

Həll: undefer ilə güləşmə — detal üçün content-i heç təxirə salmayan ayrıca baza.
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import undefer

from app.api.v1.routes.news import _BASE, _DETAIL_BASE
from app.models import News


def _cols(stmt) -> str:
    """Qurulmuş SELECT-in sütun siyahısı — davranışı yoxlayır, daxili strukturu yox."""
    return str(stmt.compile()).lower()


def test_detail_query_compiles():
    """Regresiya: bu sorğu QURULA bilməlidir (əvvəl 500 verirdi)."""
    assert _cols(_DETAIL_BASE.where(News.id == 1))


def test_detail_selects_content():
    """Detal `content` GÖSTƏRİR → SELECT-də olmalıdır."""
    sql = _cols(_DETAIL_BASE.where(News.id == 1))
    assert "news.content" in sql, "detal content-i gətirmir → səhifə boş qalar"
    # ağır vektor sütunu isə hələ də təxirdədir
    assert "news.embedding" not in sql


def test_list_still_defers_content():
    """Siyahı content-i TƏXİRƏ salmalıdır — hər sətir üçün megabaytlarla JSON."""
    sql = _cols(_BASE)
    for heavy in ("news.content", "news.embedding", "news.forecast", "news.content_tr"):
        assert heavy not in sql, f"{heavy} siyahıda təxirə salınmayıb"
    # amma adi sütunlar gəlir
    assert "news.title" in sql


def test_the_old_pattern_still_raises():
    """Köhnə naxış HƏLƏ DƏ qırıqdır — yəni test həqiqi bug-u pinləyir.

    Kimsə `undefer`-i geri gətirsə, bu test niyə olmayacağını sənədləşdirir.
    """
    bad = _BASE.where(News.id == 1).options(undefer(News.content))
    with pytest.raises(InvalidRequestError, match="conflict"):
        bad.compile()


def test_no_undefer_in_module():
    """`undefer` bu modula qayıtmamalıdır."""
    import inspect

    from app.api.v1.routes import news

    code = "\n".join(
        ln
        for ln in inspect.getsource(news).splitlines()
        if not ln.strip().startswith("#")
    )
    assert "undefer(" not in code
