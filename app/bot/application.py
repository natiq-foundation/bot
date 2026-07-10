import logging

from telegram.ext import Application
from telegram.request import HTTPXRequest

from app.bot.handlers.start import get_handler
from app.core.config import get_settings
from app.core.container import Container

logger = logging.getLogger(__name__)


def create_application(container: Container) -> Application:
    settings = get_settings()

    request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    builder = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .request(request)
    )

    if settings.BOT_API:
        builder = builder.base_url(
            settings.BOT_API.rstrip("/") + "/bot"
        ).base_file_url(
            settings.BOT_API.rstrip("/") + "/file/bot"
        )

    application = builder.build()

    application.bot_data["container"] = container

    application.add_handler(get_handler())

    logger.info("Telegram handlers registered.")

    return application
