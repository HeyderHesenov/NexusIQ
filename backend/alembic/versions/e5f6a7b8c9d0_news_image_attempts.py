"""news: şəkil çəkmə cəhdlərinin izlənməsi

`enrich_images.backfill` `image_url IS NULL` seçirdi və cəhd-izləməsi YOX idi.
Zibil sətirlərində URL "artıq cəhd edilib" markeri rolunu oynayırdı, NULL
sətirlərdə isə marker ümumiyyətlə yox idi → həmin sətirlər hər dövrdə (saatda
iki dəfə + hər restartda) yenidən çəkilirdi. Bu sütunlar həm o döngəni dayandırır,
həm də zibil sətirlərini təhlükəsiz yenidən skan etməyə imkan verir (backoff ilə).

Additive: `server_default='0'` PG11+ cədvəli yenidən yazmır.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'news',
        sa.Column(
            'image_attempts', sa.SmallInteger(), server_default='0', nullable=False
        ),
    )
    op.add_column(
        'news',
        sa.Column('image_attempted_at', sa.DateTime(timezone=True), nullable=True),
    )
    # backfill predikatı məhz bu iki sütun üzrə süzür.
    op.create_index(
        'ix_news_image_retry', 'news', ['image_attempts', 'image_attempted_at']
    )


def downgrade() -> None:
    op.drop_index('ix_news_image_retry', table_name='news')
    op.drop_column('news', 'image_attempted_at')
    op.drop_column('news', 'image_attempts')
