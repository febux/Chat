"""Make ix_messages_channel_created_at_desc actually DESC

The composite index on (channel_id, created_at) was created ASC despite its
``_desc`` name. The channel-history read path orders ``created_at DESC, id
DESC``; make the index genuinely DESC so it serves that path with a forward
scan and the name is no longer misleading.

Revision ID: 7f3a9c2e1b4d
Revises: e908fde3f956
Create Date: 2026-06-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3a9c2e1b4d'
down_revision: Union[str, Sequence[str], None] = 'e908fde3f956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate the channel-history index as (channel_id, created_at DESC)."""
    op.drop_index(
        'ix_messages_channel_created_at_desc',
        table_name='messages',
        postgresql_using='btree',
    )
    op.create_index(
        'ix_messages_channel_created_at_desc',
        'messages',
        [sa.text('channel_id'), sa.text('created_at DESC')],
        unique=False,
        postgresql_using='btree',
    )


def downgrade() -> None:
    """Restore the index to plain ASC order."""
    op.drop_index(
        'ix_messages_channel_created_at_desc',
        table_name='messages',
        postgresql_using='btree',
    )
    op.create_index(
        'ix_messages_channel_created_at_desc',
        'messages',
        ['channel_id', 'created_at'],
        unique=False,
        postgresql_using='btree',
    )
