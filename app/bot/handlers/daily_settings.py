from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from zoneinfo import ZoneInfo

from app.bot.guards.permissions import can_use_buttons
from app.bot.jobs.daily_ayah import schedule_user_daily_ayah
from app.core.config import get_settings
from app.core.constants import TIMEZONE_CONTINENTS
from app.i18n import detect_language, get_message
from app.ui.helpers import safe_edit_message_text as _safe_edit_message_text
from app.ui.keyboards import main_menu_keyboard

if TYPE_CHECKING:
    from app.database.repositories.chat import ChatRepository

logger = logging.getLogger(__name__)


def _resolve_telegram_id(update: Update) -> int | None:
    """
    Resolve the chat identifier used to look up a user in the database.

    ``/start`` stores the record under ``effective_user.id``. On some Bot API
    forks (e.g. Bale) the effective user/chats can differ, so we fall back to
    ``effective_chat.id`` before giving up. This makes the daily-settings panel
    reliably open instead of falling back to the welcome text.
    """
    if update.effective_user and update.effective_user.id is not None:
        return update.effective_user.id

    if update.effective_chat and update.effective_chat.id is not None:
        return update.effective_chat.id

    return None


async def _render_daily_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    language: str,
) -> None:
    """Render the main daily-settings panel (not rate-limited)."""
    chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

    if not chat_repo:
        logger.warning("Chat repository not available")
        settings = get_settings()
        text = f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}"
        if update.callback_query:
            await _safe_edit_message_text(
                update.callback_query, text, reply_markup=main_menu_keyboard(language)
            )
        else:
            await update.message.reply_text(
                text, reply_markup=main_menu_keyboard(language)
            )
        return

    telegram_id = _resolve_telegram_id(update)

    if telegram_id is None:
        logger.warning("Could not resolve telegram id for daily settings")
        settings = get_settings()
        text = f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}"
        if update.callback_query:
            await _safe_edit_message_text(
                update.callback_query, text, reply_markup=main_menu_keyboard(language)
            )
        else:
            await update.message.reply_text(
                text, reply_markup=main_menu_keyboard(language)
            )
        return

    chat = await chat_repo.get_by_telegram_id(telegram_id)

    if not chat:
        settings = get_settings()
        text = f"{get_message('start', language)}\n\n📱 {settings.BOT_USERNAME}"
        if update.callback_query:
            await _safe_edit_message_text(
                update.callback_query, text, reply_markup=main_menu_keyboard(language)
            )
        else:
            await update.message.reply_text(
                text, reply_markup=main_menu_keyboard(language)
            )
        return

    # Show current settings
    current_tz = chat.timezone or get_settings().DAILY_AYAH_DEFAULT_TIMEZONE
    current_time = chat.daily_time or get_settings().DAILY_AYAH_DEFAULT_TIME
    current_type = chat.daily_type or "ayah"
    delivery_mode = chat.delivery_mode or "random"
    delivery_mode_str = (
        "🔀 Random" if delivery_mode == "random" else "🔢 Sequential (Order)"
    )
    status_str = "🟢 Enabled" if chat.daily_ayah else "🔴 Disabled"
    settings = get_settings()

    message = get_message("daily_settings_current", language).format(
        timezone=current_tz,
        time=current_time,
        type=current_type,
    )
    message = f"📊 *Daily Ayah Status*: {status_str}\n🎯 *Delivery Mode*: `{delivery_mode_str}`\n\n{message}\n\n📱 {settings.BOT_USERNAME}"

    toggle_status_text = (
        "Disable Daily Ayah" if chat.daily_ayah else "Enable Daily Ayah"
    )
    toggle_status_icon = "🔴" if chat.daily_ayah else "🟢"

    # Create inline keyboard for settings navigation
    keyboard = [
        [
            InlineKeyboardButton(
                f"{toggle_status_icon} {toggle_status_text}",
                callback_data="daily_toggle_status",
            ),
        ],
        [
            InlineKeyboardButton(
                f"Mode: {delivery_mode_str}",
                callback_data="daily_delivery_mode",
            ),
        ],
        [
            InlineKeyboardButton(
                get_message("daily_settings_type", language),
                callback_data="daily_type",
            ),
        ],
        [
            InlineKeyboardButton(
                get_message("daily_settings_timezone", language),
                callback_data="daily_tz_continent",
            ),
            InlineKeyboardButton(
                get_message("daily_settings_time", language),
                callback_data="daily_time_hour",
            ),
        ],
        [
            InlineKeyboardButton(
                "⚙️ Admin Settings",
                callback_data="daily_admin_settings",
            ),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await _safe_edit_message_text(
            update.callback_query,
            message,
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
        )


async def daily_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle daily sending settings with button-based interface.

    Users can configure:
    1. Timezone (continent → city selection)
    2. Daily sending time (hour/minute buttons)
    3. Daily content type (ayah/page)
    """
    if not update.effective_user:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    try:
        await _render_daily_settings(update, context, language)
    except Exception as exc:
        logger.exception("Daily settings handler failed: error=%s", exc)
        settings = get_settings()
        if update.callback_query:
            await _safe_edit_message_text(
                update.callback_query,
                f"❌ An error occurred. Please try again.\n\n📱 {settings.BOT_USERNAME}",
                reply_markup=main_menu_keyboard(language),
            )
        elif update.message:
            await update.message.reply_text(
                f"❌ An error occurred. Please try again.\n\n📱 {settings.BOT_USERNAME}",
                reply_markup=main_menu_keyboard(language),
            )


async def daily_settings_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle callback queries from daily settings inline keyboard."""
    query = update.callback_query

    if query is None:
        return

    try:
        await query.answer()
    except BadRequest:
        pass

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if not await can_use_buttons(update, context):
        try:
            await query.answer(
                get_message("admin_only_buttons", language),
                show_alert=True,
            )
        except BadRequest:
            pass
        return

    try:
        chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

        if not chat_repo:
            logger.warning("Chat repository not available")
            settings = get_settings()
            await _safe_edit_message_text(
                query,
                f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}",
                reply_markup=main_menu_keyboard(language),
            )
            return

        telegram_id = _resolve_telegram_id(update)
        if telegram_id is None:
            return

        chat = await chat_repo.get_by_telegram_id(telegram_id)

        if not chat:
            settings = get_settings()
            await _safe_edit_message_text(
                query,
                f"{get_message('start', language)}\n\n📱 {settings.BOT_USERNAME}",
                reply_markup=main_menu_keyboard(language),
            )
            return

        callback_data = query.data

        # Handle different callback actions
        if callback_data == "daily_tz_continent":
            await show_timezone_continents(update, language)
        elif callback_data == "daily_toggle_status":
            new_status = not chat.daily_ayah
            chat = await chat_repo.update_preferences(
                telegram_id=telegram_id, daily_ayah=new_status
            )
            if chat:
                schedule_user_daily_ayah(context.application, chat)
            await _render_daily_settings(update, context, language)
        elif callback_data == "daily_time_hour":
            await show_time_hour_selection(update, language)
        elif callback_data == "daily_type":
            # Toggle between ayah and page directly
            current_type = chat.daily_type or "ayah"
            new_type = "page" if current_type == "ayah" else "ayah"
            await set_daily_type(
                update, context, chat_repo, telegram_id, new_type, language
            )
        elif callback_data.startswith("daily_tz_city_"):
            continent = callback_data.replace("daily_tz_city_", "")
            await show_timezone_cities(update, language, continent)
        elif callback_data.startswith("daily_tz_set_"):
            timezone = callback_data.replace("daily_tz_set_", "")
            await set_timezone(
                update, context, chat_repo, telegram_id, timezone, language
            )
        elif callback_data.startswith("daily_time_hour_"):
            hour = callback_data.replace("daily_time_hour_", "")
            await show_time_minute_selection(update, language, hour)
        elif callback_data.startswith("daily_time_set_"):
            time = callback_data.replace("daily_time_set_", "")
            await set_time(update, context, chat_repo, telegram_id, time, language)
        elif callback_data == "daily_delivery_mode":
            current_mode = chat.delivery_mode or "random"
            new_mode = "sequential" if current_mode == "random" else "random"
            chat = await chat_repo.update_preferences(
                telegram_id=telegram_id, delivery_mode=new_mode
            )
            await _render_daily_settings(update, context, language)
        elif callback_data == "daily_admin_settings":
            from app.bot.handlers.admin_settings import admin_settings_command

            await admin_settings_command(update, context)
            return
        elif callback_data == "daily_exit":
            # Exit daily settings and show main menu
            settings = get_settings()
            await _safe_edit_message_text(
                query,
                f"{get_message('start', language)}\n\n📱 {settings.BOT_USERNAME}",
                reply_markup=main_menu_keyboard(language),
            )
            return

    except Exception as exc:
        logger.exception("Daily settings callback failed: error=%s", exc)
        settings = get_settings()
        await _safe_edit_message_text(
            query,
            f"❌ An error occurred. Please try again.\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )


async def show_timezone_continents(update: Update, language: str) -> None:
    """Show timezone continent selection."""
    keyboard = []
    for continent in TIMEZONE_CONTINENTS.keys():
        keyboard.append(
            [
                InlineKeyboardButton(
                    continent,
                    callback_data=f"daily_tz_city_{continent}",
                )
            ]
        )
    # Continent selection footer
    keyboard.append(
        [
            InlineKeyboardButton(
                get_message("daily_settings_back", language),
                callback_data="daily_back",
            ),
        ]
    )

    await _safe_edit_message_text(
        update.callback_query,
        get_message("daily_settings_select_continent", language),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_timezone_cities(
    update: Update,
    language: str,
    continent: str,
) -> None:
    """Show timezone cities for selected continent."""
    cities = TIMEZONE_CONTINENTS.get(continent, [])
    keyboard = []

    # Show cities in rows of 2
    for i in range(0, len(cities), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                cities[i],
                callback_data=f"daily_tz_set_{cities[i]}",
            )
        )
        if i + 1 < len(cities):
            row.append(
                InlineKeyboardButton(
                    cities[i + 1],
                    callback_data=f"daily_tz_set_{cities[i + 1]}",
                )
            )
        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(
                get_message("daily_settings_back", language),
                callback_data="daily_tz_continent",
            ),
        ]
    )

    await _safe_edit_message_text(
        update.callback_query,
        get_message("daily_settings_select_city", language).format(continent=continent),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def set_timezone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_repo: ChatRepository,
    telegram_id: int,
    timezone: str,
    language: str,
) -> None:
    """Set user's timezone."""
    try:
        # Validate timezone
        ZoneInfo(timezone)

        chat = await chat_repo.update_preferences(
            telegram_id=telegram_id, timezone=timezone
        )

        if chat is not None:
            schedule_user_daily_ayah(context.application, chat)

        get_settings()
        # Show main settings panel
        await _render_daily_settings(update, context, language)

        logger.info(
            "User timezone updated: telegram_id=%s, timezone=%s", telegram_id, timezone
        )
    except Exception as e:
        logger.warning("Invalid timezone: timezone=%s, error=%s", timezone, e)
        # Use existing message or send error message
        if update.callback_query:
            get_settings()
            await _safe_edit_message_text(
                update.callback_query,
                f"❌ {get_message('timezone_set_error', language)}",
                reply_markup=main_menu_keyboard(language),
            )


async def show_time_hour_selection(update: Update, language: str) -> None:
    """Show hour selection (0-23)."""
    keyboard = []
    for hour in range(0, 24):
        row = []
        row.append(
            InlineKeyboardButton(
                f"{hour:02d}:00",
                callback_data=f"daily_time_hour_{hour}",
            )
        )
        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(
                get_message("daily_settings_back", language),
                callback_data="daily_back",
            ),
        ]
    )

    await _safe_edit_message_text(
        update.callback_query,
        get_message("daily_settings_select_hour", language),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_time_minute_selection(
    update: Update,
    language: str,
    hour: str,
) -> None:
    """Show minute selection (0-59 in 15-minute intervals)."""
    keyboard = []
    for minute in [0, 15, 30, 45]:
        row = []
        row.append(
            InlineKeyboardButton(
                f"{hour}:{minute:02d}",
                callback_data=f"daily_time_set_{hour}:{minute:02d}",
            )
        )
        keyboard.append(row)

    # Show hour selection footer
    keyboard.append(
        [
            InlineKeyboardButton(
                get_message("daily_settings_back", language),
                callback_data="daily_back",
            ),
        ]
    )

    await _safe_edit_message_text(
        update.callback_query,
        get_message("daily_settings_select_hour", language),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def set_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_repo: ChatRepository,
    telegram_id: int,
    time: str,
    language: str,
) -> None:
    """Set user's daily sending time."""
    try:
        chat = await chat_repo.update_preferences(
            telegram_id=telegram_id, daily_time=time
        )

        if chat is not None:
            schedule_user_daily_ayah(context.application, chat)

        # Show main settings panel with updated time
        await _render_daily_settings(update, context, language)

        logger.info(
            "User daily time updated: telegram_id=%s, time=%s", telegram_id, time
        )

    except Exception as e:
        logger.exception("Failed to set time: time=%s, error=%s", time, e)
        if update.callback_query:
            await _safe_edit_message_text(
                update.callback_query,
                f"❌ {get_message('time_set_error', language)}",
                reply_markup=main_menu_keyboard(language),
            )


async def set_daily_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_repo: ChatRepository,
    telegram_id: int,
    daily_type: str,
    language: str,
) -> None:
    """Set user's daily content type."""
    try:
        chat = await chat_repo.update_preferences(
            telegram_id=telegram_id, daily_type=daily_type
        )

        if chat is not None:
            schedule_user_daily_ayah(context.application, chat)

        # Show main settings panel
        await _render_daily_settings(update, context, language)

        logger.info(
            "User daily type updated: telegram_id=%s, type=%s", telegram_id, daily_type
        )

    except Exception as e:
        logger.exception("Failed to set daily type: type=%s, error=%s", daily_type, e)
        if update.callback_query:
            await _safe_edit_message_text(
                update.callback_query,
                f"❌ {get_message('daily_type_set_error', language)}",
                reply_markup=main_menu_keyboard(language),
            )
