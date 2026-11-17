from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    settings = get_settings()
    await update.message.reply_text(
        f"{get_message('help', language)}\n\n📱 {settings.BOT_USERNAME}",
        reply_markup=main_menu_keyboard(language),
    )


def get_handler() -> CommandHandler:
    return CommandHandler("help", help_command)
