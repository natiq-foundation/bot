
"""Add index used by daily-delivery queries."""

from alembic import op

revision = "6f7a8b9c0d1e"
down_revision = "5e6f7a8b9c0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_chats_daily_ayah_type_time",
        "chats",
        ["daily_ayah", "daily_type", "daily_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chats_daily_ayah_type_time",
        table_name="chats",
    )

