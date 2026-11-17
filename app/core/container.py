from __future__ import annotations

import logging

from app.api.client import APIClient
from app.api.provider import NatiqProvider
from app.bot.guards.rate_limit import configure_rate_limiter, reset_rate_limits
from app.cache.loader import QuranCacheLoader
from app.cache.quran import QuranCache
from app.cache.redis import RedisCache
from app.database.repositories.chat import ChatRepository
from app.database.repositories.sent_history import SentHistoryRepository
from app.database.session import Database

logger = logging.getLogger(__name__)


class Container:
    """
    Application dependency container.

    Responsible for:
    - Database lifecycle
    - Redis lifecycle
    - HTTP client
    - Quran cache
    - Quran provider
    - Cache loading
    - Repositories
    """

    def __init__(self) -> None:
        self._database = Database()
        self._redis = RedisCache()
        self._cache = QuranCache()
        self._http = APIClient()
        self._provider = NatiqProvider(
            client=self._http,
            cache=self._cache,
        )
        self._loader = QuranCacheLoader(
            provider=self._provider,
            cache=self._cache,
        )

        # Repositories
        self._chat_repository = ChatRepository(self._database)
        self._sent_history_repository = SentHistoryRepository(self._database)

        self._quran_cache_ready = False

        logger.info("Container initialized.")

    @property
    def database(self) -> Database:
        return self._database

    @property
    def redis(self) -> RedisCache:
        return self._redis

    @property
    def cache(self) -> QuranCache:
        return self._cache

    @property
    def http(self) -> APIClient:
        return self._http

    @property
    def provider(self) -> NatiqProvider:
        return self._provider

    @property
    def loader(self) -> QuranCacheLoader:
        return self._loader

    @property
    def chat_repository(self) -> ChatRepository:
        return self._chat_repository

    @property
    def sent_history_repository(self) -> SentHistoryRepository:
        return self._sent_history_repository

    @property
    def quran_cache_ready(self) -> bool:
        return self._quran_cache_ready

    async def startup(self) -> None:
        """
        Initialize all services.
        """
        if hasattr(self._database, "connect"):
            await self._database.connect()

        if hasattr(self._redis, "connect"):
            await self._redis.connect()

        configure_rate_limiter(self._redis)
        logger.info("Container startup completed (databases connected).")

    async def load_cache(self) -> bool:
        """
        Load Quran cache after startup.
        """
        self._quran_cache_ready = await self._loader.load()
        if not self._quran_cache_ready:
            logger.warning("Quran cache failed to load.")
        else:
            logger.info("Quran cache loaded successfully.")
        return self._quran_cache_ready

    async def reload_quran_cache(self) -> bool:
        """
        Reload the in-memory Quran cache on demand.

        Used by administrative actions to recover from a degraded cache
        without requiring a full bot restart.
        """
        self._quran_cache_ready = await self._loader.load()
        return self._quran_cache_ready

    async def shutdown(self) -> None:
        """
        Gracefully close services.
        """
        if hasattr(self._http, "close"):
            await self._http.close()

        if hasattr(self._database, "close"):
            await self._database.close()

        configure_rate_limiter(None)
        reset_rate_limits()

        if hasattr(self._redis, "close"):
            await self._redis.close()

        logger.info("Container shutdown completed.")
