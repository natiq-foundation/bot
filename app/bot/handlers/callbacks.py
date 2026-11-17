from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.bot.handlers.common import prepare_interaction
from app.bot.handlers.daily_settings import daily_settings


async def open_daily_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not await prepare_interaction(update, context, admin_only=True):
        return

    await daily_settings(update, context)


def get_callback_handlers() -> list[CallbackQueryHandler]:
    return [
        CallbackQueryHandler(
            open_daily_settings,
            pattern=r"^open_dailysettings$",
        ),
    ]
