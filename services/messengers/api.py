from services.messengers.api_like import Adapter


class Adapter(Adapter):
    platform = "PLATFORM"

    def __init__(self, token: str, api_base_url: str = ""):
        super().__init__(token, api_base_url)
