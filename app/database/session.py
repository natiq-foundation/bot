from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Database:

    def __init__(self):

        settings = get_settings()

        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def connect(self):

        async with self.engine.begin() as conn:
            await conn.run_sync(lambda _: None)

        logger.info("Database connected.")

    @asynccontextmanager
    async def session(self):

        session = self.session_factory()

        try:

            yield session

        finally:

            await session.close()

    async def dispose(self):

        await self.engine.dispose()

        logger.info("Database disconnected.")
