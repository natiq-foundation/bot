from app.api.client import APIClient


class NatiqProvider:

    def __init__(
        self,
        client: APIClient,
    ):
        self.client = client
