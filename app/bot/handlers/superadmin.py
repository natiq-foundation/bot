from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol

import psutil
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

if TYPE_CHECKING:
    from app.database.models.chat import Chat

logger = logging.getLogger(__name__)

PROCESS_START_TIME = time.time()


class SupportsAdminLookup(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> "Chat | None": ...


async def _resolve_is_superadmin(
    telegram_id: int,
    *,
    configured_admin_ids: set[int],
    chat_repository: SupportsAdminLookup,
) -> bool:
    if telegram_id in configured_admin_ids:
        return True

    try:
        chat = await chat_repository.get_by_telegram_id(telegram_id)
        if chat is None:
            return False

        if hasattr(chat, "is_admin"):
            return chat.is_admin

        return False
    except Exception as e:
        logger.warning(
            "Error checking admin status in database: telegram_id=%s, error=%s",
            telegram_id,
            e,
        )
        return False


async def _is_superadmin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    user = update.effective_user

    if user is None or user.id is None:
        return False

    settings = get_settings()
    container = context.application.bot_data.get("container")

    if not container:
        return False

    return await _resolve_is_superadmin(
        user.id,
        configured_admin_ids=settings.admin_user_ids,
        chat_repository=container.chat_repository,
    )


async def _get_system_stats(context: ContextTypes.DEFAULT_TYPE) -> str:
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    uptime_seconds = int(time.time() - PROCESS_START_TIME)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    container = context.application.bot_data.get("container")
    if container:
        user_counts = await container.chat_repository.count_by_type()
        total_users = sum(user_counts.values())
    else:
        total_users = 0

    return (
        f"🖥 CPU: {cpu_usage}%\n"
        f"💾 RAM: {ram.percent}% ({ram.used // 1024**2}MB / {ram.total // 1024**2}MB)\n"
        f"💽 Disk: {(disk.used / disk.total) * 100:.1f}% ({disk.used // 1024**3}GB / {disk.total // 1024**3}GB)\n"
        f"⏱ Server Uptime: {uptime_str}\n"
        f"👥 Total Users: {total_users}"
    )


async def _build_admin_dashboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    language: str,
    stats: str,
    totals: dict[str, int],
) -> str:
    settings = get_settings()
    container = context.application.bot_data.get("container")

    admin_names = []
    for admin_id in sorted(settings.admin_user_ids):
        display_label = f"Admin {admin_id}"
        try:
            chat_obj = await context.bot.get_chat(admin_id)
            if chat_obj.username:
                display_label = f"@{chat_obj.username}"
            elif chat_obj.first_name:
                name_parts = [chat_obj.first_name]
                if chat_obj.last_name:
                    name_parts.append(chat_obj.last_name)
                display_label = " ".join(name_parts)
        except Exception:
            pass

        admin_names.append(display_label)

    admin_list_str = ", ".join(admin_names) if admin_names else "None"

    cache_status_text = "Not Loaded"
    if container and container.loader:
        if container.loader.loading:
            cache_status_text = "🔄 Loading..."
        elif container.quran_cache_ready and container.loader.cache_loaded_at:
            loaded_at = container.loader.cache_loaded_at
            now = datetime.now(timezone.utc)
            delta = int((now - loaded_at).total_seconds())
            c_hours = delta // 3600
            c_mins = (delta % 3600) // 60
            cache_status_text = f"✅ Loaded at {loaded_at.strftime('%Y-%m-%d %H:%M:%S UTC')} (Uptime: {c_hours}h {c_mins}m)"
        elif container.quran_cache_ready:
            cache_status_text = "✅ Ready"

    env_info = (
        f"🌐 Platform: {settings.PLATFORM}\n"
        f"🌍 Language: {settings.BOT_LANGUAGE}\n"
        f"🔐 Admins: {admin_list_str}\n"
        f"🔑 API Key (Set: {'✅' if settings.BOT_TOKEN else '❌'})\n"
        f"⏱ API Timeout: {settings.NATIQ_API_TIMEOUT}s"
    )

    bot_api_info = (
        f"📍 Base URL: {settings.BOT_API}\n"
        f"🌐 Natiq API: {settings.NATIQ_API_URL}\n"
        f"🔑 API Key: {'✅ Provided' if settings.BOT_TOKEN else '❌ Missing'}"
    )

    dashboard = get_message("admin_dashboard", language).format(
        stats=stats,
        env_info=env_info,
        bot_api_info=bot_api_info,
        total_ayahs=totals["ayahs"],
        total_pages=totals["pages"],
        quran_cache_ready=cache_status_text,
        bot_id=context.bot.id,
        bot_language=settings.BOT_LANGUAGE,
        api_status="✅",
    )

    return dashboard


def _get_footer(username: str) -> str:
    return f"\n\n📱 {username}"


async def _reply_admin_denied(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    user_id = update.effective_user.id if update.effective_user else "unknown"
    message = get_message("admin_access_denied", language).format(user_id=user_id)
    settings = get_settings()

    await update.message.reply_text(
        f"{message}{_get_footer(settings.BOT_USERNAME)}",
        reply_markup=main_menu_keyboard(language),
    )


@rate_limit(
    RateLimitRule(
        limit=1,
        window_seconds=60,
    )
)
async def reload_quran_cache(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if not await _is_superadmin(update, context):
        await _reply_admin_denied(update, context)
        return

    container = context.application.bot_data.get("container")
    if not container:
        settings = get_settings()
        await update.message.reply_text(
            f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )
        return

    settings = get_settings()
    status_msg = await update.message.reply_text(
        "🔄 Reloading Quran cache... please wait.\n\n"
        "• Ayahs: ⏳ Pending\n"
        "• Takhtits: ⏳ Pending\n"
        "• Translations: ⏳ Pending\n"
        "• Surahs: ⏳ Pending"
    )

    success, details = await container.loader.load_detailed()

    def _format_status(st: str) -> str:
        if st == "success":
            return "✅ Success"
        if st.startswith("failed"):
            return f"❌ {st}"
        return f"⏳ {st}"

    report = (
        f"{'✅ Quran cache reloaded successfully!' if success else '❌ Quran cache reload failed.'}\n\n"
        f"📊 *Cache Reload Report*:\n"
        f"• Ayahs: {_format_status(details.get('ayahs', 'unknown'))}\n"
        f"• Takhtits: {_format_status(details.get('takhtits', 'unknown'))}\n"
        f"• Translations: {_format_status(details.get('translations', 'unknown'))}\n"
        f"• Surahs: {_format_status(details.get('surahs', 'unknown'))}"
    )

    try:
        await status_msg.edit_text(
            f"{report}{_get_footer(settings.BOT_USERNAME)}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(language),
        )
    except Exception:
        await update.message.reply_text(
            f"{report}{_get_footer(settings.BOT_USERNAME)}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(language),
        )


@rate_limit(
    RateLimitRule(
        limit=3,
        window_seconds=10,
    )
)
async def admin_settings_entry(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if not await _is_superadmin(update, context):
        await _reply_admin_denied(update, context)
        return

    container = context.application.bot_data.get("container")
    if not container:
        settings = get_settings()
        await update.message.reply_text(
            f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )
        return

    try:
        stats = await _get_system_stats(context)
        totals = await container.sent_history_repository.get_total_sent_counts()

        dashboard = await _build_admin_dashboard(
            update,
            context,
            language,
            stats,
            totals,
        )
        settings = get_settings()

        await update.message.reply_text(
            f"{dashboard}{_get_footer(settings.BOT_USERNAME)}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(language),
        )
    except Exception as exc:
        logger.exception("Admin settings entry failed: %s", exc)
        settings = get_settings()
        await update.message.reply_text(
            f"❌ Failed to load admin dashboard.\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )


def get_reload_cache_handler() -> CommandHandler:
    return CommandHandler("reload_cache", reload_quran_cache)
