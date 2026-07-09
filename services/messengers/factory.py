from config import Config
from services.messengers.api_like import Adapter


def build_adapters():

    adapters = {}

    if not Config.BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing in .env"
        )

    adapters[Config.PLATFORM_NAME] = Adapter(
        token=Config.BOT_TOKEN,
        api_base_url=Config.PLATFORM_API,
        platform=Config.PLATFORM_NAME,
    )

    return adapters
