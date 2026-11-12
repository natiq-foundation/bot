from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ApplicationHandlerStop, ContextTypes, TypeHandler

from app.core.config import get_settings
from app.i18n import detect_language, get_message

logger = logging.getLogger(__name__)


class SupportsRateLimitIncrement(Protocol):
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int: ...


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    message: str | None = None


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def is_allowed(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        now = time.monotonic()
        window_start = now - window_seconds
        hits = self._hits.setdefault(key, deque())

        while hits and hits[0] <= window_start:
            _ = hits.popleft()

        if len(hits) >= limit:
            return False

        hits.append(now)

        # Opportunistically prune stale keys so the fallback limiter doesn't
        # grow unboundedly with the number of distinct chats/endpoints.
        if len(self._hits) > self._MAX_KEYS:
            expired = [k for k, d in self._hits.items() if not d]
            for k in expired:
                self._hits.pop(k, None)

        return True

    _MAX_KEYS = 10_000


class RedisRateLimiter:
    def __init__(self, redis_cache: SupportsRateLimitIncrement) -> None:
        self._redis_cache: SupportsRateLimitIncrement = redis_cache

    async def is_allowed(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        current = await self._redis_cache.increment(
            key,
            window_seconds=window_seconds,
        )
        return current <= limit


_memory_rate_limiter = InMemoryRateLimiter()
_redis_rate_limiter: RedisRateLimiter | None = None


def configure_rate_limiter(
    redis_cache: SupportsRateLimitIncrement | None,
) -> None:
    global _redis_rate_limiter

    if redis_cache is None:
        _redis_rate_limiter = None
        return

    _redis_rate_limiter = RedisRateLimiter(redis_cache)


def reset_rate_limits() -> None:
    """Clear the in-memory fallback limiter (used on shutdown and in tests)."""
    global _memory_rate_limiter
    _memory_rate_limiter = InMemoryRateLimiter()


# Every interactive action has an explicit rule. ``DEFAULT_RULE`` is the safety
# net for future commands/callbacks, so a newly added button is never silently
# left without a rate limit.
COMMAND_RULES: dict[str, RateLimitRule] = {
    "start": RateLimitRule(limit=3, window_seconds=10),
    "help": RateLimitRule(limit=5, window_seconds=15),
    "random": RateLimitRule(limit=5, window_seconds=15),
    "randompage": RateLimitRule(limit=3, window_seconds=30),
    "dailysettings": RateLimitRule(limit=5, window_seconds=60),
    "timezone": RateLimitRule(limit=3, window_seconds=30),
    "admin_settings": RateLimitRule(limit=10, window_seconds=60),
    "superadmin": RateLimitRule(limit=3, window_seconds=10),
    "reload_cache": RateLimitRule(limit=1, window_seconds=60),
}

CALLBACK_RULES: dict[str, RateLimitRule] = {
    "random_ayah": RateLimitRule(limit=5, window_seconds=15),
    "next_ayah": RateLimitRule(limit=5, window_seconds=15),
    "random_page": RateLimitRule(limit=3, window_seconds=30),
    "next_page": RateLimitRule(limit=3, window_seconds=30),
    "page_translation": RateLimitRule(limit=5, window_seconds=15),
    "page_no_translation": RateLimitRule(limit=5, window_seconds=15),
    "open_dailysettings": RateLimitRule(limit=5, window_seconds=60),
    "daily_settings": RateLimitRule(limit=20, window_seconds=60),
    "admin_settings": RateLimitRule(limit=20, window_seconds=60),
}

DEFAULT_RULE = RateLimitRule(limit=20, window_seconds=60)


def _command_name(update: Update) -> str | None:
    message = update.effective_message
    text = (message.text or "").strip() if message else ""

    if not text.startswith("/"):
        return None

    command = text.split(maxsplit=1)[0][1:]
    return command.split("@", 1)[0].lower() or None


def _callback_scope(data: str | None) -> str | None:
    if not data:
        return None

    # The daily-settings and admin wizards use many dynamic callback names.
    # Treat each wizard as one logical action so the whole flow is limited
    # consistently instead of only the "root" buttons.
    if data.startswith("daily_"):
        return "daily_settings"
    if data.startswith("aset_"):
        return "admin_settings"

    return data.split(":", 1)[0]


def resolve_rate_limit_action(update: Update) -> str:
    if update.callback_query is not None:
        scope = _callback_scope(update.callback_query.data)
        return f"callback:{scope}" if scope else "callback:unknown"

    command = _command_name(update)
    if command:
        return f"command:{command}"

    return "message"


def resolve_rate_limit_rule(action: str) -> RateLimitRule:
    kind, _, name = action.partition(":")

    if kind == "command":
        return COMMAND_RULES.get(name, DEFAULT_RULE)

    if kind == "callback":
        return CALLBACK_RULES.get(name, DEFAULT_RULE)

    return DEFAULT_RULE


def _resolve_actor_key(update: Update) -> str | None:
    user = update.effective_user
    chat = update.effective_chat

    if user is not None and user.id is not None:
        if chat is not None and chat.id is not None:
            return f"user:{user.id}:chat:{chat.id}"
        return f"user:{user.id}"

    if chat is not None and chat.id is not None:
        return f"chat:{chat.id}"

    return None


def _is_rate_limitable(update: Update) -> bool:
    # Membership updates and other service updates do not represent a user
    # action and must never be dropped by the limiter.
    return update.callback_query is not None or update.effective_message is not None


async def _reply_rate_limited(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
) -> None:
    settings = get_settings()
    message_with_username = f"{message}\n\n📱 {settings.BOT_USERNAME}"

    if update.callback_query is not None:
        try:
            await update.callback_query.answer(
                message_with_username,
                show_alert=False,
            )
        except BadRequest:
            # Query already answered or expired; fall back to editing the message.
            try:
                await update.callback_query.edit_message_text(message_with_username)
            except BadRequest:
                pass
        return

    if update.message is not None:
        await update.message.reply_text(message_with_username)
        return

    if update.effective_chat is not None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_with_username,
        )


async def is_rate_limited_allowed(
    key: str,
    *,
    limit: int,
    window_seconds: int,
) -> bool:
    if _redis_rate_limiter is not None:
        try:
            return await _redis_rate_limiter.is_allowed(
                key,
                limit=limit,
                window_seconds=window_seconds,
            )
        except Exception as exc:
            logger.warning(
                "Redis rate limiter failed, falling back to memory: %s",
                exc,
            )

    return _memory_rate_limiter.is_allowed(
        key,
        limit=limit,
        window_seconds=window_seconds,
    )


async def enforce_rate_limit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Global rate-limit guard.

    Registered in an earlier handler group, this runs before every command,
    menu button and inline callback. When the limit is exceeded it answers the
    callback (or replies to the message) and raises ``ApplicationHandlerStop``
    so the actual handler never runs. Keeping the guard global is what makes
    the rate limit cover the whole bot rather than a hand-picked subset of
    handlers.
    """
    if not _is_rate_limitable(update):
        return

    actor_key = _resolve_actor_key(update)
    if actor_key is None:
        return

    action = resolve_rate_limit_action(update)
    rule = resolve_rate_limit_rule(action)

    allowed = await is_rate_limited_allowed(
        f"rate_limit:{action}:{actor_key}",
        limit=rule.limit,
        window_seconds=rule.window_seconds,
    )

    if allowed:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )
    message = rule.message or get_message("rate_limited", language)
    await _reply_rate_limited(update, context, message)
    raise ApplicationHandlerStop


def get_rate_limit_handler() -> TypeHandler:
    return TypeHandler(Update, enforce_rate_limit)
