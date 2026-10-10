from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        timeout = httpx.Timeout(
            connect=self._settings.NATIQ_API_TIMEOUT,
            read=self._settings.NATIQ_API_TIMEOUT * 2,
            write=self._settings.NATIQ_API_TIMEOUT,
            pool=self._settings.NATIQ_API_TIMEOUT * 2,
        )
        headers = self._settings.api_headers
        self._client = httpx.AsyncClient(
            base_url=self._settings.NATIQ_PRIMARY_API.rstrip("/"),
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        secondary = self._settings.NATIQ_SECONDARY_API
        self._secondary_client = (
            httpx.AsyncClient(
                base_url=secondary.rstrip("/"),
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
            if secondary
            and secondary.rstrip("/") != self._settings.NATIQ_PRIMARY_API.rstrip("/")
            else None
        )

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        return endpoint if endpoint.startswith("/") else f"/{endpoint}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        endpoint = self._normalize_endpoint(endpoint)
        try:
            response = await self._client.request(
                method, endpoint, params=params, json=json
            )
        except (httpx.ConnectError, httpx.TimeoutException):
            if self._secondary_client is None:
                raise
            logger.warning("Primary Natiq API unavailable; trying secondary endpoint")
            response = await self._secondary_client.request(
                method, endpoint, params=params, json=json
            )
        if response.is_error:
            logger.warning(
                "Natiq API %s %s returned HTTP %s",
                method,
                endpoint,
                response.status_code,
            )
            response.raise_for_status()
        return response

    async def get(
        self, endpoint: str, *, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        return await self._request("GET", endpoint, params=params)

    async def post(
        self, endpoint: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        return await self._request("POST", endpoint, json=json)

    async def put(
        self, endpoint: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        return await self._request("PUT", endpoint, json=json)

    async def patch(
        self, endpoint: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        return await self._request("PATCH", endpoint, json=json)

    async def delete(self, endpoint: str) -> httpx.Response:
        return await self._request("DELETE", endpoint)

    async def close(self) -> None:
        await self._client.aclose()
        if self._secondary_client is not None:
            await self._secondary_client.aclose()
