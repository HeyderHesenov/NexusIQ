"""news_asset link table

Xəbər ↔ aktiv bağlantısı — şəxsi digest / portfel / doğruluq kartının bünövrəsi.
YALNIZ ƏLAVƏ: create_table + create_index. `news` cədvəlinə heç bir ALTER yox.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-16 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'news_asset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('news_id', sa.Integer(), nullable=False),
        sa.Column('asset_key', sa.String(length=32), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(length=10), nullable=False),
        sa.Column('impact_dir', sa.String(length=8), nullable=True),
        sa.Column('sentiment', sa.Float(), nullable=True),
        sa.Column('impact_score', sa.Float(), nullable=True),
        sa.Column('scored_dir', sa.String(length=8), nullable=True),
        sa.Column('ret_1', sa.Float(), nullable=True),
        sa.Column('ret_5', sa.Float(), nullable=True),
        sa.Column('ret_30', sa.Float(), nullable=True),
        sa.Column('hit_1', sa.Boolean(), nullable=True),
        sa.Column('hit_5', sa.Boolean(), nullable=True),
        sa.Column('hit_30', sa.Boolean(), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.ForeignKeyConstraint(['news_id'], ['news.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'news_id', 'asset_key', 'source', name='uq_news_asset_link'
        ),
    )
    op.create_index(
        'ix_news_asset_key_published',
        'news_asset',
        ['asset_key', sa.text('published_at DESC NULLS LAST')],
    )
    op.create_index(
        'ix_news_asset_pending', 'news_asset', ['source', 'scored_at']
    )
    op.create_index('ix_news_asset_news', 'news_asset', ['news_id'])


def downgrade() -> None:
    op.drop_index('ix_news_asset_news', table_name='news_asset')
    op.drop_index('ix_news_asset_pending', table_name='news_asset')
    op.drop_index('ix_news_asset_key_published', table_name='news_asset')
    op.drop_table('news_asset')
