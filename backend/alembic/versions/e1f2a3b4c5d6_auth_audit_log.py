"""auth audit log

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('event', sa.String(length=32), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=200), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_audit_created', 'auth_audit_log', ['created_at'], unique=False)
    op.create_index('ix_auth_audit_user_created', 'auth_audit_log', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_auth_audit_user_created', table_name='auth_audit_log')
    op.drop_index('ix_auth_audit_created', table_name='auth_audit_log')
    op.drop_table('auth_audit_log')
