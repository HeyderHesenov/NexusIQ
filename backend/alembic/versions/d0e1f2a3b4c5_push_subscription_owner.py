"""push_subscriptions ownership (user_id NOT NULL)

Faza 4 Addım 12. Mövcud sətirlər ATRİBUTSUZDUR (sahibi bilinmir) → SİLİNİR; frontend
self-heal (Addım 11) authed yükləmədə yenidən abunə edir. Nullable sahib daimi
"bu sətir kimindir?" budağı = növbəti IDOR — ona görə NOT NULL.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Atributsuz köhnə sətirləri sil (self-heal yenidən abunə edəcək).
    op.execute("DELETE FROM push_subscriptions")
    op.add_column(
        'push_subscriptions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        'fk_push_subscriptions_user', 'push_subscriptions', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index('ix_push_subscriptions_user', 'push_subscriptions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_push_subscriptions_user', table_name='push_subscriptions')
    op.drop_constraint('fk_push_subscriptions_user', 'push_subscriptions', type_='foreignkey')
    op.drop_column('push_subscriptions', 'user_id')
