from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.i18n import get_message


def random_ayah_keyboard(
    ayah_uuid: str,
    language: str,
    include_settings: bool = False,
) -> InlineKeyboardMarkup:
    """
    Keyboard for ayah navigation.
    """
    rows = [
        [
            InlineKeyboardButton(
                text=get_message(
                    "next_ayah_button",
                    language,
                ),
                callback_data=f"next_ayah:{ayah_uuid}",
            ),
        ]
    ]
    if include_settings:
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_message("main_menu_daily_settings_button", language),
                    callback_data="open_dailysettings",
                ),
            ]
        )
    return InlineKeyboardMarkup(rows)


def random_page_keyboard(
    ayah_uuid: str,
    language: str,
    show_translation: bool = False,
    include_settings: bool = False,
) -> InlineKeyboardMarkup:
    """
    Keyboard for page navigation.
    """
    if show_translation:
        nav_row = [
            InlineKeyboardButton(
                text=get_message(
                    "next_page_button",
                    language,
                ),
                callback_data=f"next_page:{ayah_uuid}",
            ),
            InlineKeyboardButton(
                text=get_message(
                    "page_no_translation_button",
                    language,
                ),
                callback_data=f"page_no_translation:{ayah_uuid}",
            ),
        ]
    else:
        nav_row = [
            InlineKeyboardButton(
                text=get_message(
                    "next_page_button",
                    language,
                ),
                callback_data=f"next_page:{ayah_uuid}",
            ),
            InlineKeyboardButton(
                text=get_message(
                    "page_translation_button",
                    language,
                ),
                callback_data=f"page_translation:{ayah_uuid}",
            ),
        ]

    rows = [nav_row]
    if include_settings:
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_message("main_menu_daily_settings_button", language),
                    callback_data="open_dailysettings",
                ),
            ]
        )

    return InlineKeyboardMarkup(rows)
