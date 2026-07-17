"""auth tables (users, identities, sessions, reset/verify tokens)

Faza 4 Addım 2 — YALNIZ ƏLAVƏ: 5 yeni cədvəl. Mövcud cədvəllərə ALTER yox;
heç bir mövcud kod bunları oxumur. UUID PK (uuid4 Python-da, pgcrypto yox).

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_pk():
    return sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False)


def _created_at():
    return sa.Column(
        'created_at', sa.DateTime(timezone=True),
        server_default=sa.text('now()'), nullable=False,
    )


def _updated_at():
    return sa.Column(
        'updated_at', sa.DateTime(timezone=True),
        server_default=sa.text('now()'), nullable=False,
    )


def upgrade() -> None:
    # ---- users ----
    op.create_table(
        'users',
        _uuid_pk(),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=80), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('role', sa.String(length=16), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('failed_login_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'sessions_valid_from', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
        # Skriptdən belə normalizasiyasız email DÜŞMƏSİN.
        sa.CheckConstraint('email = lower(email)', name='ck_users_email_lower'),
    )

    # ---- user_identities ----
    op.create_table(
        'user_identities',
        _uuid_pk(),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(length=16), nullable=False),
        sa.Column('provider_subject', sa.String(length=255), nullable=False),
        sa.Column('email_at_link', sa.String(length=254), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_subject', name='uq_identity_provider_sub'),
    )
    op.create_index('ix_user_identities_user', 'user_identities', ['user_id'])

    # ---- auth_sessions ----
    op.create_table(
        'auth_sessions',
        _uuid_pk(),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
        sa.Column('previous_token_hash', sa.String(length=64), nullable=True),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'issued_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'last_used_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.String(length=24), nullable=True),
        sa.Column('user_agent', sa.String(length=200), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        _created_at(),
        _updated_at(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token_hash', name='uq_auth_sessions_refresh_hash'),
    )
    op.create_index('ix_auth_sessions_user_revoked', 'auth_sessions', ['user_id', 'revoked_at'])
    op.create_index('ix_auth_sessions_expires', 'auth_sessions', ['expires_at'])
    op.create_index(
        'ix_auth_sessions_prev_hash', 'auth_sessions', ['previous_token_hash'],
        postgresql_where=sa.text('previous_token_hash IS NOT NULL'),
    )

    # ---- password_reset_tokens ----
    op.create_table(
        'password_reset_tokens',
        _uuid_pk(),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_ip', sa.String(length=45), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_pw_reset_token_hash'),
    )
    op.create_index('ix_pw_reset_user', 'password_reset_tokens', ['user_id'])

    # ---- email_verification_tokens ----
    op.create_table(
        'email_verification_tokens',
        _uuid_pk(),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_email_verify_token_hash'),
    )
    op.create_index('ix_email_verify_user', 'email_verification_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_email_verify_user', table_name='email_verification_tokens')
    op.drop_table('email_verification_tokens')
    op.drop_index('ix_pw_reset_user', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_index('ix_auth_sessions_prev_hash', table_name='auth_sessions')
    op.drop_index('ix_auth_sessions_expires', table_name='auth_sessions')
    op.drop_index('ix_auth_sessions_user_revoked', table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_index('ix_user_identities_user', table_name='user_identities')
    op.drop_table('user_identities')
    op.drop_table('users')
