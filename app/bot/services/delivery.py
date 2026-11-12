from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from telegram import Bot, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from app.api.checker import MessengerFeature
from app.bot.views.content import format_ayah, format_page
from app.i18n import detect_language
from app.schemas.ayah import Ayah
from app.ui.keyboards.random import random_ayah_keyboard, random_page_keyboard

if TYPE_CHECKING:
    from telegram.ext import Application

logger = logging.getLogger(__name__)


def inline_keyboards_supported(application: "Application") -> bool:
    checker = application.bot_data.get("feature_checker")
    if checker is None:
        return False
    return bool(checker.supports(MessengerFeature.INLINE_KEYBOARD))


@dataclass(slots=True)
class DeliveryTarget:
    """Where and how a piece of content should be delivered."""

    bot: Bot
    chat_id: int
    language: str
    message: Message | None = None
    edit: bool = False
    inline_keyboards: bool = True

    @classmethod
    def from_update(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        edit: bool = False,
    ) -> "DeliveryTarget":
        query = update.callback_query
        message = query.message if query is not None else update.effective_message
        chat = update.effective_chat
        chat_id = message.chat_id if message is not None else (chat.id if chat else 0)

        return cls(
            bot=context.bot,
            chat_id=chat_id,
            language=detect_language(
                update.effective_user.language_code if update.effective_user else None
            ),
            message=message,
            edit=edit,
            inline_keyboards=inline_keyboards_supported(context.application),
        )

    @classmethod
    def for_chat(
        cls,
        bot: Bot,
        chat_id: int,
        language: str,
        *,
        inline_keyboards: bool = True,
    ) -> "DeliveryTarget":
        return cls(
            bot=bot,
            chat_id=chat_id,
            language=language,
            inline_keyboards=inline_keyboards,
        )


async def _send(
    target: DeliveryTarget,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if target.message is not None and target.edit:
        try:
            await target.message.edit_text(text, reply_markup=reply_markup)
            return
        except Exception as exc:
            logger.debug("Could not edit message, sending a new one: %s", exc)

    if target.message is not None and not target.edit:
        try:
            await target.message.reply_text(text, reply_markup=reply_markup)
            return
        except Exception as exc:
            logger.debug("Could not reply to message, sending a new one: %s", exc)

    await target.bot.send_message(
        chat_id=target.chat_id,
        text=text,
        reply_markup=reply_markup,
    )


async def deliver_ayah(
    target: DeliveryTarget,
    ayah: Ayah,
    *,
    include_settings: bool = False,
) -> None:
    reply_markup = None

    if target.inline_keyboards:
        reply_markup = random_ayah_keyboard(
            ayah.uuid,
            target.language,
            include_settings=include_settings,
        )

    await _send(target, format_ayah(ayah), reply_markup=reply_markup)


async def deliver_page(
    target: DeliveryTarget,
    ayahs: list[Ayah],
    *,
    show_translation: bool = False,
    include_settings: bool = False,
) -> None:
    reply_markup = None

    if target.inline_keyboards and ayahs:
        reply_markup = random_page_keyboard(
            ayahs[0].uuid,
            target.language,
            show_translation,
            include_settings=include_settings,
        )

    await _send(
        target,
        format_page(ayahs, show_translation=show_translation),
        reply_markup=reply_markup,
    )
