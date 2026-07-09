from config import Config
from services.messengers.api import Adapter


def build_adapters():
    """
    Build enabled messenger adapters.
    """

    adapters = {}

    if not Config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in .env")

    adapters["PLATFORM"] = Adapter(token=Config.BOT_TOKEN)

    return adapters
