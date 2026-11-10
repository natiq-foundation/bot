from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from app.core.exceptions import QuranUnavailableError
from app.schemas.ayah import Ayah

if TYPE_CHECKING:
    from app.core.container import Container

logger = logging.getLogger(__name__)


class QuranService:
    """
    Single entry point for content selection and sent-history recording.

    Handlers, callbacks and scheduled jobs all go through this class, so a
    random ayah, the next ayah and the daily ayah cannot drift apart.
    """

    def __init__(self, container: Container) -> None:
        self._container = container

    @classmethod
    def from_application(cls, application: object) -> "QuranService":
        bot_data = getattr(application, "bot_data", {})
        return cls.from_bot_data(bot_data)

    @classmethod
    def from_bot_data(cls, bot_data: dict) -> "QuranService":
        container = bot_data.get("container")

        if container is None:
            raise QuranUnavailableError("Container is not available")

        if not container.quran_cache_ready:
            raise QuranUnavailableError("Quran cache is not ready")

        return cls(container)

    @property
    def container(self) -> "Container":
        return self._container

    async def random_ayah(self) -> Ayah:
        return await self._container.provider.random_ayah()

    async def next_ayah(self, current_uuid: str | None) -> Ayah:
        return await self._container.provider.next_ayah(current_uuid=current_uuid)

    async def random_page(self) -> list[Ayah]:
        return await self._container.provider.random_page()

    async def page_for_ayah(self, ayah_uuid: str) -> list[Ayah]:
        return await self._container.provider.get_ayahs_by_first_ayah_uuid(
            ayah_uuid
        )

    async def next_page(self, first_ayah_uuid: str | None) -> list[Ayah]:
        if not first_ayah_uuid:
            return await self.random_page()

        current_page = await self.page_for_ayah(first_ayah_uuid)

        if not current_page or current_page[0].page is None:
            return await self.random_page()

        next_ayahs = await self._container.provider.get_ayahs_by_page(
            current_page[0].page + 1
        )
        return next_ayahs or await self.random_page()

    async def pick_ayah(
        self,
        *,
        delivery_mode: str = "random",
        chat_uuid: uuid.UUID | None = None,
    ) -> Ayah:
        if delivery_mode == "sequential" and chat_uuid is not None:
            last_uuid = (
                await self._container.sent_history_repository.get_last_sent_ayah_uuid(
                    chat_uuid=chat_uuid,
                    reading_mode="ayah",
                )
            )
            if last_uuid is not None:
                return await self.next_ayah(str(last_uuid))

        return await self.random_ayah()

    async def pick_page(
        self,
        *,
        delivery_mode: str = "random",
        chat_uuid: uuid.UUID | None = None,
    ) -> list[Ayah]:
        if delivery_mode == "sequential" and chat_uuid is not None:
            last_uuid = (
                await self._container.sent_history_repository.get_last_sent_ayah_uuid(
                    chat_uuid=chat_uuid,
                    reading_mode="page",
                )
            )
            if last_uuid is not None:
                return await self.next_page(str(last_uuid))

        return await self.random_page()

    async def record_ayah(self, telegram_id: int | None, ayah: Ayah) -> None:
        await self._record(
            telegram_id=telegram_id,
            ayah_uuid=ayah.uuid,
            reading_mode="ayah",
        )

    async def record_page(
        self,
        telegram_id: int | None,
        ayahs: list[Ayah],
    ) -> None:
        if not ayahs:
            return

        await self._record(
            telegram_id=telegram_id,
            ayah_uuid=ayahs[0].uuid,
            reading_mode="page",
        )

    async def _record(
        self,
        *,
        telegram_id: int | None,
        ayah_uuid: str,
        reading_mode: str,
    ) -> None:
        if telegram_id is None:
            return

        try:
            chat = await self._container.chat_repository.get_by_telegram_id(
                telegram_id
            )
            if chat is None:
                return

            await self._container.sent_history_repository.log_sent(
                chat_uuid=chat.uuid,
                ayah_uuid=uuid.UUID(ayah_uuid),
                reading_mode=reading_mode,
            )
        except Exception as exc:
            # Recording history must never prevent the user from receiving
            # content, so this is logged rather than raised.
            logger.warning(
                "Failed to record sent %s for telegram_id=%s: %s",
                reading_mode,
                telegram_id,
                exc,
            )
