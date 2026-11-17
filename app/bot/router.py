from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from app.bot.guards.rate_limit import get_rate_limit_handler
from app.bot.handlers.admin_settings import (
    get_admin_settings_callback_handler,
    get_admin_settings_handler,
    get_chat_member_handler,
    get_group_message_handler,
)
from app.bot.handlers.ayah import get_handlers as get_ayah_handlers
from app.bot.handlers.callbacks import get_callback_handlers
from app.bot.handlers.daily_settings import (
    daily_settings,
    daily_settings_callback,
)
from app.bot.handlers.help import get_handler as get_help_handler
from app.bot.handlers.menu import get_handler as get_main_menu_handler
from app.bot.handlers.page import get_handlers as get_page_handlers
from app.bot.handlers.start import get_handler as get_start_handler
from app.bot.handlers.superadmin import (
    admin_settings_entry,
    get_reload_cache_handler,
)


def register_handlers(application: Application) -> None:
    # The global rate-limit guard runs in the earliest handler group. Raising
    # ApplicationHandlerStop there prevents every later command, menu button
    # and callback from running while the chat is over the limit.
    application.add_handler(get_rate_limit_handler(), group=-1)

    application.add_handler(get_start_handler())
    application.add_handler(get_help_handler())
    application.add_handler(CommandHandler("superadmin", admin_settings_entry))
    application.add_handler(get_reload_cache_handler())
    application.add_handler(CommandHandler("dailysettings", daily_settings))
    application.add_handler(get_admin_settings_handler())
    application.add_handler(get_chat_member_handler())
    application.add_handler(get_group_message_handler())
    application.add_handler(get_main_menu_handler())

    # Commands and their corresponding inline callbacks are registered from
    # the same module and call the same handler function.
    for handler in get_ayah_handlers():
        application.add_handler(handler)

    for handler in get_page_handlers():
        application.add_handler(handler)

    # Every callback pattern is explicit so unrelated callbacks are not
    # swallowed when callback data eventually grows.
    for handler in get_callback_handlers():
        application.add_handler(handler)

    # Daily settings wizard callbacks are scoped to their own "daily_" prefix.
    application.add_handler(
        CallbackQueryHandler(
            daily_settings_callback,
            pattern=r"^daily_",
        )
    )

    # Admin settings callbacks are scoped to their own "aset_" prefix.
    application.add_handler(get_admin_settings_callback_handler())
