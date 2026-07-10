from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.database.models.base import Base
from app.database.models.mixins import (
    TimestampMixin,
    UUIDMixin,
)


class Favorite(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    """
    User favorite ayahs.
    """

    __tablename__ = "favorites"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "ayah_uuid",
            name="uq_user_ayah",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    ayah_uuid: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    user = relationship(
        "User",
        back_populates="favorites",
    )
