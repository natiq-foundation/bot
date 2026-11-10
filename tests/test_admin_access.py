import asyncio

from app.bot.guards.permissions import resolve_is_superadmin


class StubChat:
    """Minimal stub mimicking the Chat model for testing."""

    def __init__(self, is_admin: bool) -> None:
        self.is_admin = is_admin


class StubChatRepository:
    def __init__(self, *, is_admin: bool) -> None:
        self._is_admin = is_admin
        self.calls: list[int] = []

    async def get_by_telegram_id(self, telegram_id: int) -> StubChat | None:
        self.calls.append(telegram_id)
        if self._is_admin:
            return StubChat(is_admin=True)
        return None


def test_resolve_is_superadmin_allows_env_configured_admin_without_db_lookup() -> None:
    repository = StubChatRepository(is_admin=False)

    result = asyncio.run(
        resolve_is_superadmin(
            123,
            configured_admin_ids={123},
            chat_repository=repository,
        )
    )

    assert result is True
    assert repository.calls == []


def test_resolve_is_superadmin_falls_back_to_database_flag() -> None:
    repository = StubChatRepository(is_admin=True)

    result = asyncio.run(
        resolve_is_superadmin(
            456,
            configured_admin_ids=set(),
            chat_repository=repository,
        )
    )

    assert result is True
    assert repository.calls == [456]


def test_resolve_is_superadmin_denies_when_neither_source_grants_access() -> None:
    repository = StubChatRepository(is_admin=False)

    result = asyncio.run(
        resolve_is_superadmin(
            789,
            configured_admin_ids={111},
            chat_repository=repository,
        )
    )

    assert result is False
    assert repository.calls == [789]
