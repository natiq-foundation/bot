"""remove user profile fields from chats

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-09-17 12:30:00.000000+00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "4d5e6f7a8b9c"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("chats", "username")
    op.drop_column("chats", "first_name")
    op.drop_column("chats", "last_name")


def downgrade() -> None:
    op.add_column("chats", sa.Column("last_name", sa.String(length=128), nullable=True))
    op.add_column(
        "chats", sa.Column("first_name", sa.String(length=128), nullable=True)
    )
    op.add_column("chats", sa.Column("username", sa.String(length=64), nullable=True))
