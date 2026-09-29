import logging
from typing import Any

import httpx

from src.core.config import Settings
from src.services.errors import NojoAPIRequestError

logger = logging.getLogger(__name__)


def _error_message(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    message = payload.get("message") if isinstance(payload, dict) else None
    return message if isinstance(message, str) and message else None


class NojoClient:
    """Calls the Nojo platform's resource APIs with an already-exchanged Nojo JWT."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._base_url = settings.nojo_api_base_url

    async def get(
        self, jwt: str, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        return await self._request("GET", jwt, path, params=params)

    async def delete(self, jwt: str, path: str) -> Any:
        return await self._request("DELETE", jwt, path)

    async def post(self, jwt: str, path: str, body: dict[str, Any]) -> Any:
        return await self._request("POST", jwt, path, json=body)

    async def patch(self, jwt: str, path: str, body: dict[str, Any]) -> Any:
        return await self._request("PATCH", jwt, path, json=body)

    async def put(self, jwt: str, path: str, body: dict[str, Any]) -> Any:
        return await self._request("PUT", jwt, path, json=body)

    async def _request(
        self,
        method: str,
        jwt: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = await self._http_client.request(
                method,
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {jwt}"},
                json=json,
                params=params,
            )
        except httpx.TransportError as exc:
            logger.warning("nojo_api_failed path=%s reason=transport", path)
            raise NojoAPIRequestError(
                f"The Nojo platform API is unreachable ({path})."
            ) from exc

        if not response.is_success:
            logger.warning(
                "nojo_api_failed path=%s status_code=%s", path, response.status_code
            )
            raise NojoAPIRequestError(
                f"The Nojo platform API returned {response.status_code} for {path}.",
                status_code=response.status_code,
                detail=_error_message(response),
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.warning("nojo_api_failed path=%s reason=malformed_response", path)
            raise NojoAPIRequestError(
                f"The Nojo platform API returned an unexpected response for {path}."
            ) from exc
