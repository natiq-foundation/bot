from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import wraps

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot.guards.permissions import can_use_buttons
from app.bot.views.content import with_footer
from app.core.exceptions import QuranUnavailableError
from app.i18n import detect_language, get_message

logger = logging.getLogger(__name__)

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


def update_language(update: Update) -> str:
    return detect_language(
        update.effective_user.language_code if update.effective_user else None
    )


def user_telegram_id(update: Update) -> int | None:
    user = update.effective_user
    if user is not None and user.id is not None:
        return user.id

    chat = update.effective_chat
    if chat is not None:
        return chat.id

    return None


def callback_argument(update: Update) -> str | None:
    query = update.callback_query
    if query is None or not query.data:
        return None

    _, separator, argument = query.data.partition(":")
    return argument if separator else None


async def prepare_interaction(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    admin_only: bool = False,
) -> bool:
    """
    Common callback preamble.

    Answers the callback immediately (so Telegram stops showing the loading
    spinner) and enforces group-admin permissions when requested. Commands and
    menu-button messages pass straight through.
    """
    query = update.callback_query

    if query is None:
        return True

    if admin_only and not await can_use_buttons(update, context):
        try:
            await query.answer(
                get_message("admin_only_buttons", update_language(update)),
                show_alert=True,
            )
        except BadRequest:
            pass
        return False

    try:
        await query.answer()
    except BadRequest:
        pass

    return True


async def send_error(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_key: str,
) -> None:
    text = with_footer(get_message(message_key, update_language(update)))
    query = update.callback_query

    if query is not None:
        try:
            await query.answer(text, show_alert=True)
            return
        except BadRequest:
            pass

    message = update.effective_message
    if message is not None:
        await message.reply_text(text)
        return

    chat = update.effective_chat
    if chat is not None:
        await context.bot.send_message(chat_id=chat.id, text=text)


def handle_content_errors(
    error_key: str,
    *,
    unavailable_key: str | None = None,
) -> Callable[[Handler], Handler]:
    """Turn unexpected content errors into a single localized user message."""

    def decorator(func: Handler) -> Handler:
        @wraps(func)
        async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
        ) -> None:
            try:
                await func(update, context)
            except QuranUnavailableError:
                logger.warning("Quran cache is not ready in %s", func.__name__)
                await send_error(update, context, unavailable_key or error_key)
            except Exception:
                logger.exception("Handler %s failed", func.__name__)
                await send_error(update, context, error_key)

        return wrapper

    return decorator
