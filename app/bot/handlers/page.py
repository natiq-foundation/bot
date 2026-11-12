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
from app.bot.services.delivery import DeliveryTarget, deliver_page
from app.bot.services.quran import QuranService
from app.schemas.ayah import Ayah

logger = logging.getLogger(__name__)


async def _send_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    selector,
    *,
    show_translation: bool | None = None,
    edit: bool = False,
) -> None:
    service = QuranService.from_bot_data(context.application.bot_data)
    ayahs: list[Ayah] = await selector(service)

    if not ayahs:
        raise RuntimeError("No page content available")

    context.user_data["current_page"] = ayahs[0].page

    if show_translation is None:
        show_translation = bool(context.user_data.get("show_translation", False))

    await service.record_page(user_telegram_id(update), ayahs)
    await deliver_page(
        DeliveryTarget.from_update(update, context, edit=edit),
        ayahs,
        show_translation=show_translation,
    )


@handle_content_errors(
    "random_page_error",
    unavailable_key="random_page_loading",
)
async def random_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a random page (used by /randompage, the menu button and callbacks)."""
    if not await prepare_interaction(update, context, admin_only=True):
        return

    context.user_data["show_translation"] = False
    await _send_page(
        update,
        context,
        lambda service: service.random_page(),
        show_translation=False,
    )


@handle_content_errors("random_page_error")
async def next_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send the page after the one encoded in the callback data."""
    if not await prepare_interaction(update, context, admin_only=True):
        return

    first_ayah_uuid = callback_argument(update)
    await _send_page(
        update,
        context,
        lambda service: service.next_page(first_ayah_uuid),
    )


@handle_content_errors("random_page_error")
async def toggle_page_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show or hide translations for the current page (one shared handler)."""
    query = update.callback_query

    if query is None:
        return

    if not await prepare_interaction(update, context, admin_only=True):
        return

    show_translation = bool(query.data and query.data.startswith("page_translation:"))
    context.user_data["show_translation"] = show_translation

    first_ayah_uuid = callback_argument(update)
    await _send_page(
        update,
        context,
        lambda service: _page_or_random(service, first_ayah_uuid),
        show_translation=show_translation,
        edit=True,
    )


async def _page_or_random(
    service: QuranService,
    first_ayah_uuid: str | None,
) -> list[Ayah]:
    if first_ayah_uuid:
        ayahs = await service.page_for_ayah(first_ayah_uuid)
        if ayahs:
            return ayahs

    return await service.random_page()


def get_handlers() -> list[CommandHandler | CallbackQueryHandler]:
    return [
        CommandHandler("randompage", random_page),
        CallbackQueryHandler(random_page, pattern=r"^random_page$"),
        CallbackQueryHandler(next_page, pattern=r"^next_page:"),
        CallbackQueryHandler(
            toggle_page_translation,
            pattern=r"^page_translation:",
        ),
        CallbackQueryHandler(
            toggle_page_translation,
            pattern=r"^page_no_translation:",
        ),
    ]
