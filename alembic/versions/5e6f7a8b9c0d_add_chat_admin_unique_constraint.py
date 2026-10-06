"""add unique constraint for chat administrators

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-09-24 12:00:00.000000+00:00
"""

from __future__ import annotations

from alembic import op

revision = "5e6f7a8b9c0d"
down_revision = "4d5e6f7a8b9c"
branch_labels = None
depends_on = None


_CONSTRAINT = "uq_chat_admin_chat_user"


def upgrade() -> None:
    # Older deployments created chat_admins without the constraint declared by
    # the SQLAlchemy model. Remove duplicate rows before creating it so this
    # migration is safe for databases that already contain admin records.
    op.execute("""
        DELETE FROM chat_admins a
        USING chat_admins b
        WHERE a.uuid > b.uuid
          AND a.chat_id = b.chat_id
          AND a.admin_telegram_id = b.admin_telegram_id
        """)
    op.create_unique_constraint(
        _CONSTRAINT,
        "chat_admins",
        ["chat_id", "admin_telegram_id"],
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "chat_admins", type_="unique")
