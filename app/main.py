import asyncio
import logging

import httpx

from app.bot.application import create_application
from app.core.config import get_settings
from app.core.container import Container
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


async def main():
    configure_logging()

    settings = get_settings()

    logger.info("Starting Quran Bot...")

    container = Container()

    try:
        #
        # Initialize services
        #

        await container.startup()

        logger.info("All services initialized.")

        #
        # Verify Bot API endpoint
        #

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.BOT_API)

        logger.info(
            "Bot API reachable (%s): %s",
            response.status_code,
            settings.BOT_API,
        )

        #
        # Build Telegram application
        #

        application = create_application(container)

        logger.info("Initializing Telegram application...")

        await application.initialize()

        logger.info("Starting Telegram application...")

        await application.start()

        if application.updater is None:
            raise RuntimeError("Updater is not available.")

        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=None,
        )

        logger.info("Bot is now polling.")

        while True:
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("Stopping bot...")

    finally:
        try:
            if "application" in locals():
                if application.updater is not None:
                    await application.updater.stop()

                await application.stop()
                await application.shutdown()
        finally:
            await container.shutdown()

        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
