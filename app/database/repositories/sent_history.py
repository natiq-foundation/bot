from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select

if TYPE_CHECKING:
    from app.database.models.sent_history import SentHistory
    from app.database.session import Database

logger = logging.getLogger(__name__)


class SentHistoryRepository:
    def __init__(self, database: "Database") -> None:
        self._database = database

    async def log_sent(
        self,
        *,
        chat_uuid: uuid.UUID,
        ayah_uuid: uuid.UUID,
        reading_mode: str = "ayah",
    ) -> "SentHistory":
        from app.database.models.sent_history import ReadingMode, SentHistory

        mode = ReadingMode(reading_mode)
        history = SentHistory(
            chat_uuid=chat_uuid,
            ayah_uuid=ayah_uuid,
            type=mode,
        )
        async with self._database.session() as session:
            session.add(history)
            await session.commit()
            await session.refresh(history)
            return history

    async def get_last_sent_ayah_uuid(
        self,
        *,
        chat_uuid: uuid.UUID,
        reading_mode: str = "ayah",
    ) -> uuid.UUID | None:
        """Return the ayah UUID of the most recent send for a chat/mode."""
        from app.database.models.sent_history import ReadingMode, SentHistory

        mode = ReadingMode(reading_mode)
        stmt = (
            select(SentHistory.ayah_uuid)
            .where(
                SentHistory.chat_uuid == chat_uuid,
                SentHistory.type == mode,
            )
            .order_by(SentHistory.created_at.desc())
            .limit(1)
        )

        async with self._database.session() as session:
            return await session.scalar(stmt)

    async def get_total_sent_counts(self) -> dict[str, int]:
        from app.database.models.sent_history import ReadingMode, SentHistory

        async with self._database.session() as session:
            ayah_stmt = select(func.count(SentHistory.uuid)).where(
                SentHistory.type == ReadingMode.AYAH
            )
            page_stmt = select(func.count(SentHistory.uuid)).where(
                SentHistory.type == ReadingMode.PAGE
            )

            ayahs_count = await session.scalar(ayah_stmt) or 0
            pages_count = await session.scalar(page_stmt) or 0

            return {"ayahs": ayahs_count, "pages": pages_count}
