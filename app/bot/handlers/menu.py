from __future__ import annotations

from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.bot.handlers.ayah import random_ayah
from app.bot.handlers.daily_settings import daily_settings
from app.bot.handlers.page import random_page
from app.i18n import detect_language, get_message
from app.ui.keyboards.main_menu import main_menu_keyboard, quran_menu_keyboard

MenuAction = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]

_MENU_ROUTES: tuple[tuple[str, MenuAction], ...] = (
    ("main_menu_random_button", random_ayah),
    ("main_menu_random_page_button", random_page),
    ("main_menu_daily_settings_button", daily_settings),
)


async def dispatch_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message or not update.message.text:
        return

    if update.message.text.startswith("/"):
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    text = update.message.text

    # Check if Quran button pressed
    if text == get_message("main_menu_quran_button", language):
        await update.message.reply_text(
            get_message("quran_menu_title", language),
            reply_markup=quran_menu_keyboard(language),
        )
        return

    # Check if Back button pressed
    if text == get_message("main_menu_back_button", language):
        await update.message.reply_text(
            get_message("start", language),
            reply_markup=main_menu_keyboard(language),
        )
        return

    # Check submenu routes
    for message_key, action in _MENU_ROUTES:
        if text == get_message(message_key, language):
            await action(update, context)
            return


def get_handler() -> MessageHandler:
    return MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        dispatch_main_menu,
    )
