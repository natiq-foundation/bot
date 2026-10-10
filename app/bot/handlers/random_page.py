from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards.random import random_page_keyboard

if TYPE_CHECKING:
    from app.core.container import Container

logger = logging.getLogger(__name__)


async def generate_random_page(container: Container) -> list[Ayah]:
    """Generate a random page by selecting a random Quran page."""
    return await container.provider.random_page()


def format_page(
    ayahs: list[Ayah],
    *,
    show_translation: bool = False,
) -> str:
    """Format a page (group of ayahs), supporting multi-surah transitions and bismillah lines."""
    settings = get_settings()
    parts: list[str] = []

    current_surah_uuid: str | None = None
    page_num = ayahs[0].page if ayahs and ayahs[0].page else "?"

    for ayah in ayahs:
        # Check if surah changes on this page (multi-surah page transition)
        if ayah.surah_uuid != current_surah_uuid:
            current_surah_uuid = ayah.surah_uuid
            icon = ayah.surah_icon if ayah.surah_icon else "🕋"
            parts.append(f"\n{icon} *{ayah.surah_name}* (Page {page_num})")
            if ayah.show_bismillah_line and ayah.bismillah_text:
                parts.append(ayah.bismillah_text)
            parts.append("")

        parts.append(f"📖 {ayah.text} ﴿{ayah.ayah_number}﴾")

        if show_translation and ayah.translation:
            parts.append(f"📝 {ayah.translation}")
            parts.append("")

    # Attribution
    parts.append("")
    parts.append(f"📱 {settings.BOT_USERNAME}")

    return "\n".join(parts).strip()


@rate_limit(
    RateLimitRule(
        limit=3,
        window_seconds=30,
    )
)
async def random_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a random Quran page (group of ayahs)."""
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
                f"{get_message('random_page_error', language)}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        if not container.quran_cache_ready:
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_page_loading', language)}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        page_ayahs = await generate_random_page(container)

        context.user_data["show_translation"] = False

        if page_ayahs:
            context.user_data["current_page"] = page_ayahs[0].page

        if update.effective_user and page_ayahs:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=page_ayahs[0].uuid,
                    reading_mode="page",
                )

        reply_markup = None
        if (
            context.application.bot_data["feature_checker"].supports(
                MessengerFeature.INLINE_KEYBOARD
            )
            and page_ayahs
        ):
            show_translation = context.user_data.get("show_translation", False)
            reply_markup = random_page_keyboard(
                page_ayahs[0].uuid, language, show_translation
            )

        await update.message.reply_text(
            text=format_page(page_ayahs),
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.exception("Random page failed: %s", exc)
        settings = get_settings()
        await update.message.reply_text(
            f"{get_message('random_page_error', language)}\n\n📱 {settings.BOT_USERNAME}"
        )


def get_handler() -> CommandHandler:
    return CommandHandler("randompage", random_page)
