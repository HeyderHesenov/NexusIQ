"""ix_news_impact_published → DESC NULLS LAST (sorğu ilə eyni sıra)

İndeks ASC qurulmuşdu (`impact_score, published_at`), sorğu isə
`impact_score DESC NULLS LAST, published_at DESC NULLS LAST` ilə sıralayır —
ona görə planner indeksi SIRA üçün işlədə bilmirdi.

Real EXPLAIN (düzəlişdən əvvəl, 4,643 xəbər):
    Limit → Sort (top-N heapsort) → Seq Scan on news
    Buffers: shared hit=851, actual time≈7.9ms, 4,654 sətir skan → 10 sətir

Modelin öz şərhi onsuz da niyyəti "impact_score DESC, published_at DESC" kimi
yazırdı; qardaş indeks `ix_news_published` isə artıq düzgün
`published_at.desc().nullslast()` işlədir. Yəni bu, ardıcıllıq pozuntusu idi.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-17 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_news_impact_published", table_name="news")
    op.create_index(
        "ix_news_impact_published",
        "news",
        [
            sa.text("impact_score DESC NULLS LAST"),
            sa.text("published_at DESC NULLS LAST"),
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_news_impact_published", table_name="news")
    op.create_index(
        "ix_news_impact_published", "news", ["impact_score", "published_at"]
    )
