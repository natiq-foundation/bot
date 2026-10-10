"""add user profile fields to chats

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-09-17 12:00:00.000000+00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "3c4d5e6f7a8b"
down_revision = "2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("username", sa.String(length=64), nullable=True))
    op.add_column(
        "chats", sa.Column("first_name", sa.String(length=128), nullable=True)
    )
    op.add_column("chats", sa.Column("last_name", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("chats", "last_name")
    op.drop_column("chats", "first_name")
    op.drop_column("chats", "username")
