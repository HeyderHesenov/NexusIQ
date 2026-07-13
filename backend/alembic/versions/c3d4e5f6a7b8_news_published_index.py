"""news published_at index — ön səhifə (kateqoriyasız) sıralaması

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sorğu ilə eyni sıra (DESC NULLS LAST) — planner-in istifadə edə bilməsi üçün.
    op.create_index(
        'ix_news_published',
        'news',
        [sa.text('published_at DESC NULLS LAST')],
    )


def downgrade() -> None:
    op.drop_index('ix_news_published', table_name='news')
