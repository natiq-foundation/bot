from app.api.client import APIClient
from app.api.provider import NatiqProvider
from app.cache.redis import RedisCache
from app.core.config import Settings, get_settings
from app.database.session import Database


class Container:
    """
    Central dependency container.

    Every long-lived service is instantiated here and shared across
    the application.
    """

    def __init__(self) -> None:
        self._settings: Settings = get_settings()

        self._database = Database()
        self._cache = RedisCache()
        self._http = APIClient()

        self._provider = NatiqProvider(
            client=self._http,
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def settings(self) -> Settings:
        return self._settings

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------

    @property
    def database(self) -> Database:
        return self._database

    @property
    def cache(self) -> RedisCache:
        return self._cache

    @property
    def http(self) -> APIClient:
        return self._http

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    @property
    def provider(self) -> NatiqProvider:
        return self._provider

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        await self.database.connect()
        await self.cache.connect()
        await self.http.connect()

    async def shutdown(self) -> None:
        try:
            await self.http.close()
        finally:
            try:
                await self.cache.close()
            finally:
                await self.database.dispose()
