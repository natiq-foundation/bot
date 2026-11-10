from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.bot.jobs.daily_ayah import schedule_user_daily_ayah
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle /start command.

    - Auto-register user to database
    - Set default preferences
    - Enable daily ayah at configured time
    - Set default timezone
    """
    if not update.message or not update.effective_user:
        return

    telegram_id = update.effective_user.id
    language = detect_language(update.effective_user.language_code)

    try:
        # Get user repository from bot data
        user_repo = context.application.bot_data.get("user_repository")

        if user_repo:
            # Get or create user in database
            # The repository will set default timezone (Asia/Riyadh) and time (03:15) from env config
            # Enable daily ayah by default
            chat = await user_repo.get_or_create(
                telegram_id=telegram_id,
                language=language,
                enable_daily_ayah=True,
            )

            if chat is not None:
                schedule_user_daily_ayah(context.application, chat)

            logger.info("User started: telegram_id=%s", telegram_id)
        else:
            logger.warning("User repository not available")
            # Continue anyway - the bot should still respond even if database is unavailable

        # (Cleanup: remove unused admin check from /start)
        settings = get_settings()
        await update.message.reply_text(
            f"{get_message('start', language)}\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )

    except Exception as exc:
        logger.exception("Start handler failed: error=%s", exc)
        settings = get_settings()
        await update.message.reply_text(
            f"❌ An error occurred. Please try again.\n\n📱 {settings.BOT_USERNAME}"
        )


def get_handler() -> CommandHandler:
    return CommandHandler("start", start)
