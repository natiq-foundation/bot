from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from telegram import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
)

from app.bot.handlers.daily_settings import TIMEZONE_CONTINENTS
from app.core.config import get_settings
from app.database.repositories.chat import ChatRepository
from app.i18n import detect_language

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def _safe_edit_message_text(
    query: CallbackQuery,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except BadRequest:
        pass


async def _is_chat_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:
    user = update.effective_user
    if not user:
        return False

    settings = get_settings()
    if user.id in settings.admin_user_ids:
        return True

    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user.id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception as e:
        logger.debug(
            "get_chat_member check failed for chat_id=%s, user_id=%s: error=%s",
            chat_id,
            user.id,
            e,
        )

    return False


async def track_chat_membership(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Track bot added to or removed from groups/channels."""
    result: ChatMemberUpdated = update.my_chat_member
    if not result:
        return

    chat = result.chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    chat_repo: ChatRepository = context.application.bot_data.get("user_repository")
    if not chat_repo:
        return

    was_member = old_status in ("member", "administrator", "creator")
    is_member = new_status in ("member", "administrator", "creator")

    if not was_member and is_member:
        logger.info(
            "Bot added to chat: chat_id=%s, title=%s, type=%s",
            chat.id,
            chat.title,
            chat.type,
        )
        if chat.type in ("group", "supergroup", "channel"):
            try:
                language = detect_language(
                    update.effective_user.language_code
                    if update.effective_user
                    else None
                )
                db_chat = await chat_repo.get_or_create(
                    telegram_id=chat.id,
                    chat_type=chat.type,
                    language=language,
                    enable_daily_ayah=True,
                )
                from app.bot.jobs.daily_ayah import schedule_user_daily_ayah

                schedule_user_daily_ayah(context.application, db_chat)
                logger.info(
                    "Successfully registered and scheduled daily ayah for added chat: chat_id=%s",
                    chat.id,
                )

                # Fetch and save admins
                try:
                    admins = await context.bot.get_chat_administrators(chat.id)
                    admin_ids = [
                        admin.user.id for admin in admins if not admin.user.is_bot
                    ]
                    await chat_repo.save_chat_admins(chat.id, chat.type, admin_ids)
                    logger.info(
                        "Saved %d admins for chat_id=%s", len(admin_ids), chat.id
                    )
                except Exception as e:
                    logger.error("Failed to save admins for chat_id=%s: %s", chat.id, e)

                try:
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=(
                            "🤖 *Natiq Quran Bot Connected!*\n\n"
                            "This chat has been successfully registered for daily Quran ayahs and pages.\n"
                            "Administrators can configure sending times, types, and preferences using /admin_settings."
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as msg_err:
                    logger.warning(
                        "Could not send welcome message to chat_id=%s: error=%s",
                        chat.id,
                        msg_err,
                    )
            except Exception as exc:
                logger.exception(
                    "Failed to register chat on membership update: error=%s", exc
                )


async def _render_chat_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    language: str,
) -> None:
    chat_repo: ChatRepository = context.application.bot_data.get("user_repository")
    if not chat_repo:
        return

    chat = await chat_repo.get_by_telegram_id(chat_id)
    if not chat:
        chat = await chat_repo.get_or_create(
            telegram_id=chat_id, chat_type="group", language=language
        )

    chat_title = str(chat_id)
    try:
        tg_chat = await context.bot.get_chat(chat_id)
        if tg_chat.title:
            chat_title = tg_chat.title
    except Exception:
        pass

    status_str = "🟢 Enabled" if chat.daily_ayah else "🔴 Disabled"
    timezone_str = chat.timezone or get_settings().DAILY_AYAH_DEFAULT_TIMEZONE
    time_str = chat.daily_time or get_settings().DAILY_AYAH_DEFAULT_TIME
    type_str = "📖 Ayah" if chat.daily_type == "ayah" else "📄 Page"

    message = (
        f"⚙️ *Admin Settings*\n\n"
        f"📌 *Chat*: {chat_title}\n"
        f"🏷 *Type*: `{chat.chat_type}`\n"
        f"📊 *Daily Ayah Status*: {status_str}\n"
        f"🌍 *Timezone*: `{timezone_str}`\n"
        f"⏰ *Delivery Time*: `{time_str}`\n"
        f"📖 *Content Type*: {type_str}\n\n"
        f"⚙️ *Manage settings below (Admin/Owner access only):*"
    )

    toggle_status_text = (
        "Disable Daily Ayah" if chat.daily_ayah else "Enable Daily Ayah"
    )
    toggle_status_icon = "🔴" if chat.daily_ayah else "🟢"

    keyboard = [
        [
            InlineKeyboardButton(
                f"{toggle_status_icon} {toggle_status_text}",
                callback_data=f"aset_toggle_{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                f"📖 Type: {chat.daily_type.capitalize()}",
                callback_data=f"aset_type_{chat_id}",
            ),
            InlineKeyboardButton(
                "⏰ Time",
                callback_data=f"aset_time_{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🌍 Timezone",
                callback_data=f"aset_tz_{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Back / Chats",
                callback_data="aset_list",
            ),
            InlineKeyboardButton(
                "❌ Close",
                callback_data="aset_exit",
            ),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await _safe_edit_message_text(
            update.callback_query,
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="Markdown"
        )


async def _reply_or_edit(
    update: Update,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    if update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except Exception:
            pass
    if update.effective_message:
        await update.effective_message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )


async def admin_settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /admin_settings command for chat administrators and owners."""
    if not update.effective_user:
        return

    language = detect_language(update.effective_user.language_code)
    chat = update.effective_chat

    if not chat:
        return

    logger.info(
        "User %s requested /admin_settings in chat_id=%s (type=%s)",
        update.effective_user.id,
        chat.id,
        chat.type,
    )

    chat_repo: ChatRepository = context.application.bot_data.get("user_repository")
    if not chat_repo:
        await _reply_or_edit(update, "Service temporarily unavailable.")
        return

    user_id = update.effective_user.id
    settings = get_settings()
    is_superadmin = user_id in settings.admin_user_ids

    if chat.type in ("group", "supergroup", "channel"):
        if not is_superadmin and not await _is_chat_admin(update, context, chat.id):
            await _reply_or_edit(
                update,
                "❌ You must be an administrator or owner with management permissions to configure this chat.",
            )
            return

        # Persist admin relationship
        await chat_repo.add_chat_admin(chat.id, chat.type, user_id)

        db_chat = await chat_repo.get_by_telegram_id(chat.id)
        if not db_chat:
            db_chat = await chat_repo.get_or_create(
                telegram_id=chat.id, chat_type=chat.type, language=language
            )

        await _render_chat_settings(update, context, chat.id, language)
        return

    # Private/direct chat: list user's managed groups/channels
    managed_chats = await chat_repo.list_chats_administered_by(user_id)
    all_chats = await chat_repo.list_group_chats()
    raw_admin_chats = list(managed_chats)
    seen_chat_ids = {c.chat_id for c in raw_admin_chats}

    for c in all_chats:
        if c.chat_id not in seen_chat_ids:
            if await _is_chat_admin(update, context, c.chat_id):
                raw_admin_chats.append(c)
                seen_chat_ids.add(c.chat_id)

    # Filter to only groups, supergroups, and channels (exclude private chats)
    admin_chats = [
        c for c in raw_admin_chats if c.chat_type in ("group", "supergroup", "channel")
    ]

    if not admin_chats:
        await _reply_or_edit(
            update,
            "ℹ️ You do not have any managed groups or channels where this bot is added.\n\n"
            "Add the bot to your group or channel as an admin and use /admin_settings.",
        )
        return

    if len(admin_chats) == 1:
        await _render_chat_settings(update, context, admin_chats[0].chat_id, language)
        return

    keyboard = []
    for c in admin_chats:
        title = str(c.chat_id)
        try:
            tg_chat = await context.bot.get_chat(c.chat_id)
            if tg_chat.title:
                title = tg_chat.title
        except Exception:
            pass
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"👥 {title} ({c.chat_type})",
                    callback_data=f"aset_menu_{c.chat_id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="aset_exit")])

    await _reply_or_edit(
        update,
        "⚙️ *Admin Settings*\n\nSelect a group or channel you manage to configure:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def admin_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for admin settings."""
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
    data = query.data

    chat_repo: ChatRepository = context.application.bot_data.get("user_repository")
    if not chat_repo:
        return

    try:
        if data == "aset_list":
            all_chats = await chat_repo.list_group_chats()
            admin_db_chats = await chat_repo.list_chats_administered_by(
                update.effective_user.id
            )
            seen_chat_ids = {c.chat_id for c in admin_db_chats}
            admin_chats = list(admin_db_chats)

            for c in all_chats:
                if c.chat_id not in seen_chat_ids:
                    if await _is_chat_admin(update, context, c.chat_id):
                        admin_chats.append(c)
                        seen_chat_ids.add(c.chat_id)

            if not admin_chats:
                await _safe_edit_message_text(
                    query, "No managed groups or channels found."
                )
                return

            keyboard = []
            for c in admin_chats:
                title = str(c.chat_id)
                try:
                    tg_chat = await context.bot.get_chat(c.chat_id)
                    if tg_chat.title:
                        title = tg_chat.title
                except Exception:
                    pass
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"👥 {title} ({c.chat_type})",
                            callback_data=f"aset_menu_{c.chat_id}",
                        )
                    ]
                )

            keyboard.append(
                [InlineKeyboardButton("❌ Close", callback_data="aset_exit")]
            )
            await _safe_edit_message_text(
                query,
                "Select a chat or channel to configure settings:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        elif data == "aset_exit":
            await _safe_edit_message_text(query, "Settings closed.")
            return

        parts = data.split("_")
        if len(parts) < 3:
            return

        action = parts[1]
        chat_id = int(parts[2])

        settings = get_settings()
        is_superadmin = (
            update.effective_user
            and update.effective_user.id in settings.admin_user_ids
        )

        if not is_superadmin and not await _is_chat_admin(update, context, chat_id):
            await query.answer(
                "❌ You must be an administrator or owner with management permissions.",
                show_alert=True,
            )
            return

        chat = await chat_repo.get_by_telegram_id(chat_id)
        if not chat:
            await query.answer("Chat not found in database.", show_alert=True)
            return

        if action == "menu":
            await _render_chat_settings(update, context, chat_id, language)

        elif action == "toggle":
            new_status = not chat.daily_ayah
            chat = await chat_repo.update_preferences(
                telegram_id=chat_id, daily_ayah=new_status
            )
            if chat:
                from app.bot.jobs.daily_ayah import schedule_user_daily_ayah

                schedule_user_daily_ayah(context.application, chat)
            logger.info(
                "Admin updated daily_ayah status: chat_id=%s, daily_ayah=%s",
                chat_id,
                new_status,
            )
            await _render_chat_settings(update, context, chat_id, language)

        elif action == "type":
            new_type = "page" if chat.daily_type == "ayah" else "ayah"
            chat = await chat_repo.update_preferences(
                telegram_id=chat_id, daily_type=new_type
            )
            if chat:
                from app.bot.jobs.daily_ayah import schedule_user_daily_ayah

                schedule_user_daily_ayah(context.application, chat)
            logger.info(
                "Admin updated daily_type: chat_id=%s, daily_type=%s",
                chat_id,
                new_type,
            )
            await _render_chat_settings(update, context, chat_id, language)

        elif action == "time":
            keyboard = []
            for hour in range(0, 24):
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"{hour:02d}:00", callback_data=f"aset_th_{chat_id}_{hour}"
                        )
                    ]
                )
            keyboard.append(
                [InlineKeyboardButton("🔙 Back", callback_data=f"aset_menu_{chat_id}")]
            )
            await _safe_edit_message_text(
                query,
                "Select delivery hour:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif data.startswith(f"aset_th_{chat_id}_"):
            hour = parts[3]
            keyboard = []
            for minute in [0, 15, 30, 45]:
                time_str = f"{hour}:{minute:02d}"
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            time_str, callback_data=f"aset_ts_{chat_id}_{time_str}"
                        )
                    ]
                )
            keyboard.append(
                [InlineKeyboardButton("🔙 Back", callback_data=f"aset_time_{chat_id}")]
            )
            await _safe_edit_message_text(
                query,
                f"Select delivery minute for {hour}:00:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif data.startswith(f"aset_ts_{chat_id}_"):
            time_str = parts[3]
            chat = await chat_repo.update_preferences(
                telegram_id=chat_id, daily_time=time_str
            )
            if chat:
                from app.bot.jobs.daily_ayah import schedule_user_daily_ayah

                schedule_user_daily_ayah(context.application, chat)
            logger.info(
                "Admin updated daily time: chat_id=%s, time=%s",
                chat_id,
                time_str,
            )
            await _render_chat_settings(update, context, chat_id, language)

        elif action == "tz":
            keyboard = []
            for continent in TIMEZONE_CONTINENTS.keys():
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            continent, callback_data=f"aset_tzc_{chat_id}_{continent}"
                        )
                    ]
                )
            keyboard.append(
                [InlineKeyboardButton("🔙 Back", callback_data=f"aset_menu_{chat_id}")]
            )
            await _safe_edit_message_text(
                query, "Select continent:", reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith(f"aset_tzc_{chat_id}_"):
            continent = parts[3]
            cities = TIMEZONE_CONTINENTS.get(continent, [])
            keyboard = []
            for city in cities:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            city, callback_data=f"aset_tzs_{chat_id}_{city}"
                        )
                    ]
                )
            keyboard.append(
                [InlineKeyboardButton("🔙 Back", callback_data=f"aset_tz_{chat_id}")]
            )
            await _safe_edit_message_text(
                query,
                f"Select city in {continent}:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif data.startswith(f"aset_tzs_{chat_id}_"):
            tz_name = "_".join(parts[3:])
            try:
                ZoneInfo(tz_name)
                chat = await chat_repo.update_preferences(
                    telegram_id=chat_id, timezone=tz_name
                )
                if chat:
                    from app.bot.jobs.daily_ayah import schedule_user_daily_ayah

                    schedule_user_daily_ayah(context.application, chat)
                logger.info(
                    "Admin updated timezone: chat_id=%s, timezone=%s",
                    chat_id,
                    tz_name,
                )
            except Exception:
                pass
            await _render_chat_settings(update, context, chat_id, language)

    except Exception as exc:
        logger.exception("Admin settings callback failed: error=%s", exc)


def get_admin_settings_handler() -> CommandHandler:
    return CommandHandler("admin_settings", admin_settings_command)


def get_admin_settings_callback_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(admin_settings_callback, pattern=r"^aset_")


def get_chat_member_handler() -> ChatMemberHandler:
    return ChatMemberHandler(track_chat_membership, ChatMemberHandler.MY_CHAT_MEMBER)


async def auto_register_group_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Auto-register group or supergroup when any message is received."""
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return

    chat_repo: ChatRepository = context.application.bot_data.get("user_repository")
    if chat_repo:
        try:
            language = detect_language(
                update.effective_user.language_code if update.effective_user else None
            )
            await chat_repo.get_or_create(
                telegram_id=chat.id, chat_type=chat.type, language=language
            )
        except Exception:
            pass


def get_group_message_handler() -> MessageHandler:
    from telegram.ext import filters

    return MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND,
        auto_register_group_message,
    )
