"""Add is_admin flag to users

Revision ID: 3049219cdef6
Revises: 4924863e8714
Create Date: 2026-11-07 16:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine.mock import MockConnection

# revision identifiers, used by Alembic.
revision: str = '3049219cdef6'
down_revision: Union[str, Sequence[str], None] = '4924863e8714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if isinstance(bind, MockConnection):
        op.add_column(
            "users",
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
        return

    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "is_admin" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if isinstance(bind, MockConnection):
        op.drop_column("users", "is_admin")
        return

    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "is_admin" in columns:
        op.drop_column("users", "is_admin")
