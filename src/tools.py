import logging
from dataclasses import dataclass
from typing import Any

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from src.core.config import Settings
from src.services.auth import ExchangeTokenVerifier, NojoAccessToken
from src.services.nojo_client import NojoClient

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    client: httpx.AsyncClient
    settings: Settings
    verifier: ExchangeTokenVerifier
    nojo_client: NojoClient


ServerContext = Context[AppState, Any]

_READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)


def _caller() -> NojoAccessToken:
    access_token = get_access_token()
    if not isinstance(access_token, NojoAccessToken):  # pragma: no cover
        raise ToolError(
            "No Nojo credentials on this request. Ask the user to reconnect "
            "the Nojo connector."
        )
    return access_token


async def whoami(ctx: ServerContext) -> dict[str, Any]:
    caller = _caller()
    logger.info("whoami_succeeded sub=%s client_id=%s", caller.subject, caller.client_id)
    return {
        "subject": caller.subject,
        "client_id": caller.client_id,
        "token_expires_at": caller.expires_at,
        "exchange": "ok",
    }


async def get_current_user(ctx: ServerContext) -> Any:
    caller = _caller()
    logger.info("get_current_user_called sub=%s", caller.subject)
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.get_current_user(caller.nojo_jwt)


async def list_farms(ctx: ServerContext) -> Any:
    caller = _caller()
    logger.info("list_farms_called sub=%s", caller.subject)
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.list_farms(caller.nojo_jwt)


async def list_crops(ctx: ServerContext) -> Any:
    caller = _caller()
    logger.info("list_crops_called sub=%s", caller.subject)
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.list_crops(caller.nojo_jwt)


async def list_alerts(ctx: ServerContext) -> Any:
    caller = _caller()
    logger.info("list_alerts_called sub=%s", caller.subject)
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.list_alerts(caller.nojo_jwt)


async def list_stations(ctx: ServerContext) -> Any:
    caller = _caller()
    logger.info("list_stations_called sub=%s", caller.subject)
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.list_stations(caller.nojo_jwt)


_DESCRIPTIONS = {
    whoami: (
        "Report which Nojo account this connection is authenticated as.\n\n"
        'Returns {"subject": str, "client_id": str, "token_expires_at": int, '
        '"exchange": "ok"}.\n'
        "`subject` is the Nojo user id behind the current session. A successful "
        "call confirms the whole sign-in chain worked; it makes no other request."
    ),
    get_current_user: (
        "Get the Nojo profile of the authenticated user.\n\n"
        'Returns {"id": str, "name": str, "phone": str, "role": str}.'
    ),
    list_farms: "List all farms owned by the authenticated farmer. Returns an array of farms.",
    list_crops: (
        "List all crops across every farm owned by the authenticated farmer. "
        "Returns an array of crops."
    ),
    list_alerts: (
        "List active alerts across the authenticated farmer's farms, for today "
        "plus the next 3 days. Returns an array of alerts."
    ),
    list_stations: (
        "List the authenticated farmer's IoT station devices. Returns an array "
        "of stations."
    ),
}


def register_tools(mcp: MCPServer[AppState]) -> None:
    for tool, description in _DESCRIPTIONS.items():
        mcp.tool(annotations=_READ_ONLY, description=description)(tool)
