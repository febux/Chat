"""Partial unique indexes for users soft delete

Revision ID: 4924863e8714
Revises: 7f3a9c2e1b4d
Create Date: 2026-11-07 16:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4924863e8714'
down_revision: Union[str, Sequence[str], None] = '7f3a9c2e1b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add soft-delete timestamp to the users table.
    op.add_column(
        'users',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Replace full unique indexes with partial ones that only cover active users.
    # This allows a deleted user's email/username to be reused for a new account
    # while still preventing duplicates among non-deleted users.
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')

    op.create_index(
        op.f('ix_users_email'),
        'users',
        ['email'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
        sqlite_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        op.f('ix_users_username'),
        'users',
        ['username'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
        sqlite_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Restore the original full unique indexes.
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')

    op.create_index(
        op.f('ix_users_username'),
        'users',
        ['username'],
        unique=True,
    )
    op.create_index(
        op.f('ix_users_email'),
        'users',
        ['email'],
        unique=True,
    )

    op.drop_column('users', 'deleted_at')
