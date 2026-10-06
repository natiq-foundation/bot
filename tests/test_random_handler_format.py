from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards import random_ayah_keyboard

logger = logging.getLogger(__name__)


def format_ayah(ayah: Ayah) -> str:
    """Format ayah with readable spacing."""
    settings = get_settings()
    parts: list[str] = []

    if ayah.surah_icon:
        parts.append(f"{ayah.surah_icon} {ayah.surah_name}")
    else:
        parts.append(ayah.surah_name)

    if ayah.show_bismillah_line and ayah.bismillah_text:
        parts.append(ayah.bismillah_text)

    parts.append(f"📖 {ayah.text} ﴿{ayah.ayah_number}﴾")

    if ayah.translation:
        parts.append(f"📝 {ayah.translation}")

    parts.append(f"📱 {settings.BOT_USERNAME}")

    return "\n\n".join(parts)


@rate_limit(
    RateLimitRule(
        limit=5,
        window_seconds=15,
    )
)
async def random_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a random Quran ayah."""
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    try:
        container = context.application.bot_data.get("container")

        if not container:
            logger.warning("Container not available")
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_ayah_error', language)}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        if not container.quran_cache_ready:
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_ayah_error', language)}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        ayah: Ayah = await container.provider.random_ayah()

        # Track in database
        if update.effective_user:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=ayah.uuid,
                    reading_mode="ayah",
                )

        reply_markup = None
        if context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        ):
            reply_markup = random_ayah_keyboard(ayah.uuid, language)

        await update.message.reply_text(
            text=format_ayah(ayah),
            reply_markup=reply_markup,
        )

    except Exception as exc:
        logger.exception("Random ayah failed: %s", exc)
        settings = get_settings()
        await update.message.reply_text(
            f"{get_message('random_ayah_error', language)}\n\n📱 {settings.BOT_USERNAME}"
        )


def get_handler() -> CommandHandler:
    return CommandHandler("random", random_ayah)
