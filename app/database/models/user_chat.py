from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin


class UserChat(
    Base,
    TimestampMixin,
):
    """
    Many-to-many relation between Telegram users
    and Telegram chats.
    """

    __tablename__ = "user_chats"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "chat_id",
            name="uq_user_chat",
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

    chat_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chats.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    user = relationship(
        "User",
        back_populates="user_chats",
    )

    chat = relationship(
        "Chat",
        back_populates="user_chats",
    )
