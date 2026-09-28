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
        self._base_url = settings.nojo_api_base_url

    async def get(self, jwt: str, path: str) -> Any:
        try:
            response = await self._http_client.get(
                f"{self._base_url}{path}", headers={"Authorization": f"Bearer {jwt}"}
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
