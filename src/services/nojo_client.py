import logging
from typing import Any

import httpx

from src.core.config import Settings
from src.services.errors import NojoAPIRequestError

logger = logging.getLogger(__name__)


class NojoClient:
    """Calls the Nojo platform's resource APIs with an already-exchanged Nojo JWT."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings

    async def get_current_user(self, jwt: str) -> Any:
        return await self._get(jwt, "/auth/me")

    async def list_farms(self, jwt: str) -> Any:
        return await self._get(jwt, "/farms")

    async def list_crops(self, jwt: str) -> Any:
        return await self._get(jwt, "/crops")

    async def list_alerts(self, jwt: str) -> Any:
        return await self._get(jwt, "/alerts")

    async def list_stations(self, jwt: str) -> Any:
        return await self._get(jwt, "/stations")

    async def _get(self, jwt: str, path: str) -> Any:
        url = f"{self._settings.nojo_api_base_url}{path}"

        try:
            response = await self._http_client.get(
                url, headers={"Authorization": f"Bearer {jwt}"}
            )
        except httpx.TransportError as exc:
            logger.warning("nojo_api_failed path=%s reason=transport", path)
            raise NojoAPIRequestError(
                f"The Nojo platform API is unreachable ({path})."
            ) from exc

        if response.status_code != 200:
            logger.warning(
                "nojo_api_failed path=%s status_code=%s", path, response.status_code
            )
            raise NojoAPIRequestError(
                f"The Nojo platform API returned {response.status_code} for {path}."
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.warning("nojo_api_failed path=%s reason=malformed_response", path)
            raise NojoAPIRequestError(
                f"The Nojo platform API returned an unexpected response for {path}."
            ) from exc
