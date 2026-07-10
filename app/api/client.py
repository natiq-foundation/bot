from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class APIClient:

    def __init__(self):

        settings = get_settings()

        self.client = httpx.AsyncClient(
            base_url=settings.NATIQ_PRIMARY_API,
            timeout=15.0,
            headers={
                "Accept": "application/json",
            },
        )

        if settings.NATIQ_API_TOKEN:
            self.client.headers["Authorization"] = (
                f"Token {settings.NATIQ_API_TOKEN}"
            )

    async def connect(self):

        logger.info("HTTP client initialized.")

    async def close(self):

        await self.client.aclose()

        logger.info("HTTP client closed.")
