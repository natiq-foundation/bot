from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from app.bot.handlers.common import (
    callback_argument,
    handle_content_errors,
    prepare_interaction,
    user_telegram_id,
)
from app.bot.services.delivery import DeliveryTarget, deliver_ayah
from app.bot.services.quran import QuranService
from app.schemas.ayah import Ayah

logger = logging.getLogger(__name__)


async def _send_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    selector,
) -> None:
    service = QuranService.from_bot_data(context.application.bot_data)
    ayah: Ayah = await selector(service)

    context.user_data["current_ayah_uuid"] = ayah.uuid
    await service.record_ayah(user_telegram_id(update), ayah)
    await deliver_ayah(DeliveryTarget.from_update(update, context), ayah)


@handle_content_errors("random_ayah_error")
async def random_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a random ayah (used by /random, the menu button and callbacks)."""
    if not await prepare_interaction(update, context, admin_only=True):
        return

    await _send_ayah(update, context, lambda service: service.random_ayah())


@handle_content_errors("next_ayah_error")
async def next_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send the ayah that follows the one encoded in the callback data."""
    if not await prepare_interaction(update, context, admin_only=True):
        return

    current_uuid = callback_argument(update)
    await _send_ayah(
        update,
        context,
        lambda service: service.next_ayah(current_uuid),
    )


def get_handlers() -> list[CommandHandler | CallbackQueryHandler]:
    return [
        CommandHandler("random", random_ayah),
        CallbackQueryHandler(random_ayah, pattern=r"^random_ayah$"),
        CallbackQueryHandler(next_ayah, pattern=r"^next_ayah:"),
    ]
