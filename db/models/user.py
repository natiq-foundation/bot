from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    """A private (direct-message) user who has talked to the bot, on any
    supported platforms"""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_user_platform_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    platform: Mapped[str] = mapped_column(String(32), index=True)

    # The chat id on that platform. Stored as a string because Rubika
    # uses opaque GUIDs, not numeric ids like the others.
    external_id: Mapped[str] = mapped_column(String(128), index=True)

    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
