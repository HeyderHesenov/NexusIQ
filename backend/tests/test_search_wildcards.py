"""LIKE jokerləri istifadəçi girişindən qaçırılmalıdır (`autoescape=True`).

Kök səbəb: `news/search` `pattern = f"%{q.strip()}%"` qurub `ilike(pattern)`
edirdi. `%` və `_` LIKE metasimvollarıdır, yəni istifadəçi girişi naxışın ÖZÜNÜ
dəyişirdi:
  - `q=_`      → hər sətri tuturdu (`_` = bir simvolluq joker)
  - `q=%`      → hər sətri tuturdu
  - `q=%_%_%`  → 4 sütun üzrə superxətti backtracking (CPU yandırma)

Data sızması YOXDUR (`limit` 50-də bağlıdır) — real təsir CPU-dur, üstəlik
endpoint tamamilə rate-limit-siz idi. `advisor.py` daha pisdir: 10 söz × 4 sütun
= 40 hücumçu formalı naxış.

Kod bazası düzgün həlli ARTIQ bilirdi — `imagejunk.junk_sql` `autoescape=True`
işlədir və şərhində bunu "HƏLLEDİCİ" adlandırır. Sadəcə bu iki yerə tətbiq
olunmamışdı.

Canlı ölçü (real DB, düzəlişdən sonra): `q=_` → 2 sətir; SQL ground truth
"4 sütunun birində LİTERAL alt-xətt olan sətir" = 2. Tam üst-üstə düşür.
Düzəlişdən əvvəl həmin sorğu 4,643 xəbərin hamısını tuturdu.
"""
from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app.models import News


def _sql(clause) -> str:
    return str(
        clause.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_contains_autoescape_emits_escape_clause():
    """`contains(..., autoescape=True)` SQL-də ESCAPE verməlidir."""
    sql = _sql(News.title.contains("50%_off", autoescape=True))
    assert "ESCAPE" in sql.upper()


def test_autoescape_neutralizes_wildcards():
    """Joker simvollar naxışda LİTERAL kimi qaçırılır.

    SQLAlchemy qaçırma simvolu olaraq `/` işlədir (`\\` deyil):
        title LIKE '%' || '/%' || '%' ESCAPE '/'
    """
    sql = _sql(News.title.contains("%", autoescape=True))
    assert "ESCAPE '/'" in sql
    assert "/%" in sql

    sql_u = _sql(News.title.contains("_", autoescape=True))
    assert "ESCAPE '/'" in sql_u
    assert "/_" in sql_u


def test_raw_ilike_would_not_escape():
    """Kontrast: xam `ilike(f'%{q}%')` qaçırmır — regresiyanın forması budur."""
    sql = _sql(News.title.ilike("%_%"))
    assert "ESCAPE" not in sql.upper()


def _code_only(src: str) -> str:
    """Şərh sətirlərini atır — assert-lər öz izah şərhimizi tutmasın."""
    return "\n".join(
        ln for ln in src.splitlines() if not ln.strip().startswith("#")
    )


def test_search_route_uses_autoescape_and_rate_limit():
    """Route xam ilike-a QAYITMAMALIDIR və limitsiz qalmamalıdır."""
    import inspect

    from app.api.v1.routes import news

    src = _code_only(inspect.getsource(news.search_news))
    assert "autoescape=True" in src
    assert 'f"%{q' not in src, "xam LIKE naxışı geri qayıdıb"
    assert ".ilike(" not in src

    mod = inspect.getsource(news)
    assert 'rate_limit("news_search"' in mod


def test_advisor_uses_autoescape():
    """Advisor RAG namizəd axtarışı da qaçırmalıdır (10 söz × 4 sütun = 40 naxış)."""
    import inspect

    from app.agents import advisor

    src = _code_only(inspect.getsource(advisor))
    assert "f.contains(w, autoescape=True)" in src
    assert 'f.ilike(f"%{w}%")' not in src
