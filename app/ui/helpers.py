from __future__ import annotations

from telegram import CallbackQuery, InlineKeyboardMarkup, Update
from telegram.error import BadRequest


async def safe_edit_message_text(
    query: CallbackQuery,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    """Edit a callback query's message, ignoring harmless Telegram errors."""
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except BadRequest:
        pass


async def safe_answer(
    query: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
) -> None:
    """Answer a callback query without letting an expired query crash a handler."""
    try:
        await query.answer(text, show_alert=show_alert)
    except BadRequest:
        pass


async def reply_or_edit(
    update: Update,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    """Edit the callback message when possible, otherwise reply to the update."""
    query = update.callback_query

    if query is not None and query.message is not None:
        try:
            await query.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except BadRequest:
            pass

    if update.effective_message is not None:
        await update.effective_message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
