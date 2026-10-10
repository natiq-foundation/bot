from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.handlers.admin_settings import _is_chat_admin
from app.bot.handlers.daily_settings import daily_settings
from app.bot.handlers.random import format_ayah
from app.bot.handlers.random_page import format_page, generate_random_page
from app.core.container import Container
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards.random import random_ayah_keyboard, random_page_keyboard

logger = logging.getLogger(__name__)


async def _check_group_permissions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return True

    if chat.type in ("group", "supergroup", "channel"):
        settings = get_settings()
        if user.id in settings.admin_user_ids:
            return True
        if await _is_chat_admin(update, context, chat.id):
            return True
        return False

    return True


async def _reply_with_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ayah: Ayah,
    edit: bool = False,
) -> None:
    query = update.callback_query

    if query is None:
        return

    message = query.message

    if message is None:
        return

    context.user_data["current_ayah_uuid"] = ayah.uuid

    reply_markup = None
    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if context.application.bot_data["feature_checker"].supports(
        MessengerFeature.INLINE_KEYBOARD
    ):
        reply_markup = random_ayah_keyboard(ayah.uuid, language)

    if edit:
        try:
            await message.edit_text(
                text=format_ayah(ayah),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    await message.reply_text(
        text=format_ayah(ayah),
        reply_markup=reply_markup,
    )


async def _reply_with_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ayahs: list[Ayah],
    edit: bool = False,
) -> None:
    query = update.callback_query

    if query is None:
        return

    message = query.message

    if message is None:
        return

    reply_markup = None
    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )
    show_translation = context.user_data.get("show_translation", False)

    if (
        context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        )
        and ayahs
    ):
        reply_markup = random_page_keyboard(ayahs[0].uuid, language, show_translation)

    if edit:
        try:
            await message.edit_text(
                text=format_page(ayahs, show_translation=show_translation),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    await message.reply_text(
        text=format_page(ayahs, show_translation=show_translation),
        reply_markup=reply_markup,
    )


async def _reply_with_page_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ayahs: list[Ayah],
    edit: bool = True,
) -> None:
    query = update.callback_query

    if query is None:
        return

    message = query.message

    if message is None:
        return

    reply_markup = None
    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if (
        context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        )
        and ayahs
    ):
        reply_markup = random_page_keyboard(ayahs[0].uuid, language, True)

    if edit:
        try:
            await message.edit_text(
                text=format_page(ayahs, show_translation=True),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    await message.reply_text(
        text=format_page(ayahs, show_translation=True),
        reply_markup=reply_markup,
    )


async def _handle_next_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    if not await _check_group_permissions(update, context):
        await query.answer(
            "❌ Only group administrators can interact with buttons.",
            show_alert=True,
        )
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("next_ayah_error"),
                show_alert=True,
            )
            return

        chat = None
        if update.effective_user:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )

        # Always fetch the true next sequential ayah of the ayah clicked
        ayah: Ayah = await container.provider.next_ayah(
            current_uuid=query.data.split(":")[1],
        )

        if chat and ayah:
            await container.sent_history_repository.log_sent(
                chat_uuid=chat.uuid,
                ayah_uuid=ayah.uuid,
                reading_mode="ayah",
            )

        await _reply_with_ayah(
            update,
            context,
            ayah,
            edit=False,
        )

    except Exception:
        logger.exception("Next ayah callback failed")
        await query.answer(
            get_message("next_ayah_error"),
            show_alert=True,
        )


async def random_ayah_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    if not await _check_group_permissions(update, context):
        await query.answer(
            "❌ Only group administrators can interact with buttons.",
            show_alert=True,
        )
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("next_ayah_error"),
                show_alert=True,
            )
            return

        chat = None
        if update.effective_user:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )

        ayah: Ayah = await container.provider.random_ayah()

        if chat and ayah:
            await container.sent_history_repository.log_sent(
                chat_uuid=chat.uuid,
                ayah_uuid=ayah.uuid,
                reading_mode="ayah",
            )

        await _reply_with_ayah(
            update,
            context,
            ayah,
            edit=False,
        )

    except Exception:
        logger.exception("Random ayah callback failed")
        await query.answer(
            get_message("next_ayah_error"),
            show_alert=True,
        )


async def _handle_next_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    if not await _check_group_permissions(update, context):
        await query.answer(
            "❌ Only group administrators can interact with buttons.",
            show_alert=True,
        )
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("random_page_error"),
                show_alert=True,
            )
            return

        chat = None
        if update.effective_user:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )

        current_ayahs = await container.provider.get_ayahs_by_first_ayah_uuid(
            query.data.split(":")[1]
        )
        current_page = (
            current_ayahs[0].page
            if current_ayahs and current_ayahs[0].page is not None
            else (context.user_data.get("current_page") or 1)
        )

        next_page = current_page + 1
        page_ayahs = await container.provider.get_ayahs_by_page(next_page)
        if not page_ayahs:
            page_ayahs = await generate_random_page(container)

        if page_ayahs:
            context.user_data["current_page"] = page_ayahs[0].page

        if chat and page_ayahs:
            await container.sent_history_repository.log_sent(
                chat_uuid=chat.uuid,
                ayah_uuid=page_ayahs[0].uuid,
                reading_mode="page",
            )

        show_translation = context.user_data.get("show_translation", False)

        if show_translation:
            await _reply_with_page_translation(
                update,
                context,
                page_ayahs,
                edit=False,
            )
        else:
            await _reply_with_page(
                update,
                context,
                page_ayahs,
                edit=False,
            )

    except Exception:
        logger.exception("Next page callback failed")
        await query.answer(
            get_message("random_page_error"),
            show_alert=True,
        )


async def _handle_page_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    if not await _check_group_permissions(update, context):
        await query.answer(
            "❌ Only group administrators can interact with buttons.",
            show_alert=True,
        )
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("random_page_error"),
                show_alert=True,
            )
            return

        context.user_data["show_translation"] = True

        first_ayah_uuid = query.data.split(":")[1]
        page_ayahs = await container.provider.get_ayahs_by_first_ayah_uuid(
            first_ayah_uuid
        )

        if not page_ayahs:
            page_ayahs = await generate_random_page(container)

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

        await _reply_with_page_translation(
            update,
            context,
            page_ayahs,
            edit=True,
        )

    except Exception:
        logger.exception("Page translation callback failed")
        await query.answer(
            get_message("random_page_error"),
            show_alert=True,
        )


async def _handle_page_no_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    if not await _check_group_permissions(update, context):
        await query.answer(
            "❌ Only group administrators can interact with buttons.",
            show_alert=True,
        )
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("random_page_error"),
                show_alert=True,
            )
            return

        context.user_data["show_translation"] = False

        first_ayah_uuid = query.data.split(":")[1]
        page_ayahs = await container.provider.get_ayahs_by_first_ayah_uuid(
            first_ayah_uuid
        )

        if not page_ayahs:
            page_ayahs = await generate_random_page(container)

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

        await _reply_with_page(
            update,
            context,
            page_ayahs,
            edit=True,
        )

    except Exception:
        logger.exception("Page no translation callback failed")
        await query.answer(
            get_message("random_page_error"),
            show_alert=True,
        )


async def _handle_open_dailysettings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    if not await _check_group_permissions(update, context):
        await query.answer(
            "❌ Only group administrators can interact with buttons.",
            show_alert=True,
        )
        return

    await query.answer()
    await daily_settings(update, context)


def get_callback_handlers() -> list[CallbackQueryHandler]:
    return [
        CallbackQueryHandler(
            random_ayah_callback,
            pattern=r"^random_ayah$",
        ),
        CallbackQueryHandler(
            _handle_next_ayah,
            pattern=r"^next_ayah:",
        ),
        CallbackQueryHandler(
            _handle_next_page,
            pattern=r"^next_page:",
        ),
        CallbackQueryHandler(
            _handle_page_translation,
            pattern=r"^page_translation:",
        ),
        CallbackQueryHandler(
            _handle_page_no_translation,
            pattern=r"^page_no_translation:",
        ),
        CallbackQueryHandler(
            _handle_open_dailysettings,
            pattern=r"^open_dailysettings$",
        ),
    ]
