import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.ext import ApplicationHandlerStop, TypeHandler

from app.bot.guards import rate_limit as rate_limit_module
from app.bot.guards.rate_limit import (
    InMemoryRateLimiter,
    enforce_rate_limit,
    resolve_rate_limit_action,
    resolve_rate_limit_rule,
)
from app.bot.router import register_handlers
from app.database.base import Base as DatabaseBase
from app.database.base import Base as ModelsBase


class StubRedisCache:
    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int:
        self.calls[key] = self.calls.get(key, 0) + 1
        return self.calls[key]


class FailingRedisCache:
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int:
        raise RuntimeError("redis unavailable")


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    rate_limit_module.configure_rate_limiter(None)
    rate_limit_module.reset_rate_limits()
    yield
    rate_limit_module.configure_rate_limiter(None)
    rate_limit_module.reset_rate_limits()


def make_update(
    *,
    callback_data: str | None = None,
    text: str | None = None,
    user_id: int = 7,
):
    message = SimpleNamespace(
        text=text,
        chat_id=-1001,
        reply_text=AsyncMock(),
    )

    query = None
    if callback_data is not None:
        query = SimpleNamespace(
            data=callback_data,
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
        )

    return SimpleNamespace(
        update_id=1,
        callback_query=query,
        effective_message=message if text is not None else None,
        message=message if text is not None else None,
        effective_user=SimpleNamespace(id=user_id, language_code="en"),
        effective_chat=SimpleNamespace(id=-1001, type="group"),
    )


def make_context():
    return SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock()),
    )


def test_in_memory_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
    assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
    assert not limiter.is_allowed("user:1", limit=2, window_seconds=60)


def test_in_memory_rate_limiter_is_scoped_per_key() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("user:1", limit=1, window_seconds=60)
    assert limiter.is_allowed("user:2", limit=1, window_seconds=60)
    assert not limiter.is_allowed("user:1", limit=1, window_seconds=60)


def test_database_base_is_unified() -> None:
    assert DatabaseBase is ModelsBase


def test_redis_rate_limiter_uses_redis_counter() -> None:
    rate_limit_module.configure_rate_limiter(StubRedisCache())

    allowed_first = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "key-1",
            limit=2,
            window_seconds=60,
        )
    )
    allowed_second = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "key-1",
            limit=2,
            window_seconds=60,
        )
    )
    blocked_third = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "key-1",
            limit=2,
            window_seconds=60,
        )
    )

    assert allowed_first is True
    assert allowed_second is True
    assert blocked_third is False


def test_redis_rate_limiter_falls_back_to_memory() -> None:
    rate_limit_module.configure_rate_limiter(FailingRedisCache())

    allowed_first = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "fallback-key",
            limit=1,
            window_seconds=60,
        )
    )
    blocked_second = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "fallback-key",
            limit=1,
            window_seconds=60,
        )
    )

    assert allowed_first is True
    assert blocked_second is False


def test_resolve_action_covers_commands_callbacks_and_menu_text() -> None:
    assert (
        resolve_rate_limit_action(make_update(text="/start@NatiqBot"))
        == "command:start"
    )
    assert (
        resolve_rate_limit_action(make_update(callback_data="next_ayah:abc"))
        == "callback:next_ayah"
    )
    assert (
        resolve_rate_limit_action(make_update(callback_data="page_translation:abc"))
        == "callback:page_translation"
    )
    assert (
        resolve_rate_limit_action(make_update(callback_data="daily_tz_city_Asia"))
        == "callback:daily_settings"
    )
    assert (
        resolve_rate_limit_action(make_update(callback_data="aset_toggle_-1001"))
        == "callback:admin_settings"
    )
    assert resolve_rate_limit_action(make_update(text="📜 Random Ayah")) == "message"


@pytest.mark.parametrize(
    "action",
    [
        "callback:next_ayah",
        "callback:next_page",
        "callback:page_translation",
        "callback:page_no_translation",
        "callback:random_ayah",
        "callback:open_dailysettings",
        "callback:daily_settings",
        "callback:admin_settings",
        "command:random",
        "command:randompage",
        "command:dailysettings",
        "message",
        "callback:brand_new_future_button",
    ],
)
def test_every_action_has_a_positive_rate_limit(action: str) -> None:
    rule = resolve_rate_limit_rule(action)
    assert rule.limit > 0
    assert rule.window_seconds > 0


def test_next_ayah_callback_is_rate_limited() -> None:
    update = make_update(callback_data="next_ayah:abc")
    context = make_context()

    for _ in range(5):
        asyncio.run(enforce_rate_limit(update, context))

    with pytest.raises(ApplicationHandlerStop):
        asyncio.run(enforce_rate_limit(update, context))

    update.callback_query.answer.assert_awaited_once()


def test_random_command_message_is_rate_limited() -> None:
    update = make_update(text="/random")
    context = make_context()

    for _ in range(5):
        asyncio.run(enforce_rate_limit(update, context))

    with pytest.raises(ApplicationHandlerStop):
        asyncio.run(enforce_rate_limit(update, context))

    update.message.reply_text.assert_awaited_once()


def test_rate_limit_is_scoped_per_user() -> None:
    first_user = make_update(callback_data="next_ayah:abc", user_id=1)
    second_user = make_update(callback_data="next_ayah:abc", user_id=2)
    context = make_context()

    for _ in range(5):
        asyncio.run(enforce_rate_limit(first_user, context))

    # A second user must not inherit the first user's exhausted bucket.
    asyncio.run(enforce_rate_limit(second_user, context))

    with pytest.raises(ApplicationHandlerStop):
        asyncio.run(enforce_rate_limit(first_user, context))


def test_service_updates_are_never_rate_limited() -> None:
    update = SimpleNamespace(
        callback_query=None,
        effective_message=None,
        message=None,
        effective_user=SimpleNamespace(id=7, language_code="en"),
        effective_chat=SimpleNamespace(id=-1001, type="group"),
    )
    context = make_context()

    for _ in range(50):
        asyncio.run(enforce_rate_limit(update, context))


def test_router_registers_the_global_guard_before_other_handlers() -> None:
    class FakeApplication:
        def __init__(self) -> None:
            self.added = []

        def add_handler(self, handler, group: int = 0) -> None:
            self.added.append((handler, group))

    application = FakeApplication()
    register_handlers(application)

    first_handler, first_group = application.added[0]
    assert first_group == -1
    assert isinstance(first_handler, TypeHandler)
