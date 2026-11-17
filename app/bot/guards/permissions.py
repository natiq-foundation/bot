from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.database.models.chat import Chat

logger = logging.getLogger(__name__)


class SupportsAdminLookup(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> "Chat | None": ...


async def resolve_is_superadmin(
    telegram_id: int,
    *,
    configured_admin_ids: set[int],
    chat_repository: SupportsAdminLookup,
) -> bool:
    if telegram_id in configured_admin_ids:
        return True

    try:
        chat = await chat_repository.get_by_telegram_id(telegram_id)
        if chat is None:
            return False

        return bool(getattr(chat, "is_admin", False))
    except Exception as exc:
        logger.warning(
            "Error checking admin status in database: telegram_id=%s, error=%s",
            telegram_id,
            exc,
        )
        return False


async def is_superadmin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    user = update.effective_user
    if user is None or user.id is None:
        return False

    container = context.application.bot_data.get("container")
    if container is None:
        return False

    return await resolve_is_superadmin(
        user.id,
        configured_admin_ids=get_settings().admin_user_ids,
        chat_repository=container.chat_repository,
    )


async def is_chat_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:
    user = update.effective_user
    if user is None:
        return False

    if user.id in get_settings().admin_user_ids:
        return True

    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user.id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception as exc:
        logger.debug(
            "get_chat_member check failed for chat_id=%s, user_id=%s: error=%s",
            chat_id,
            user.id,
            exc,
        )

    return False


async def can_use_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Return True when the current user may interact with inline buttons."""
    chat = update.effective_chat
    user = update.effective_user

    if chat is None or user is None:
        return True

    if chat.type in ("group", "supergroup", "channel"):
        if user.id in get_settings().admin_user_ids:
            return True
        return await is_chat_admin(update, context, chat.id)

    return True
