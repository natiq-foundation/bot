from __future__ import annotations

import uuid

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.database.models.base import Base
from app.database.models.mixins import (
    TimestampMixin,
    UUIDMixin,
)
from app.database.types import UUIDType


class User(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )

    username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    translation_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(),
        nullable=True,
    )

    recitation_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(),
        nullable=True,
    )

    preferred_mushaf_uuid: Mapped[
        uuid.UUID | None
    ] = mapped_column(
        UUIDType(),
        nullable=True,
    )

    #
    # Relationships
    #

    favorites = relationship(
        "Favorite",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    reading_progress = relationship(
        "ReadingProgress",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    user_chats = relationship(
        "UserChat",
        back_populates="user",
        cascade="all, delete-orphan",
    )
