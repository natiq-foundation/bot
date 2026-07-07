from services.messengers.telegram_like import TelegramLikeAdapter


class TelegramAdapter(TelegramLikeAdapter):
    platform = "telegram"

    def __init__(self, token: str, api_base_url: str = "https://api.telegram.org"):
        super().__init__(token, api_base_url)
