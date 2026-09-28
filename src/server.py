import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.config import Settings
from src.services.auth import ExchangeTokenVerifier
from src.services.nojo_client import NojoClient
from src.tools import AppState, register_tools

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
The Nojo MCP server. whoami reports which Nojo account the connection is authenticated \
as. get_current_user, list_farms, list_crops, list_alerts, and list_stations call the \
Nojo platform API on behalf of the authenticated user to report their profile, farms, \
crops, active alerts, and IoT stations.\
"""


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"Accept": "application/json"},
        timeout=settings.http_timeout_seconds,
        limits=httpx.Limits(max_connections=settings.http_max_connections),
    )


def build_server(settings: Settings) -> MCPServer[AppState]:
    verifier = ExchangeTokenVerifier(settings)

    @asynccontextmanager
    async def lifespan(_: MCPServer[AppState]) -> AsyncIterator[AppState]:
        client = build_http_client(settings)
        verifier.http_client = client
        logger.info(
            "nojo_mcp_starting issuer=%s resource=%s",
            settings.issuer_url,
            settings.resource_server_url,
        )
        try:
            yield AppState(nojo_client=NojoClient(client, settings))
        finally:
            verifier.http_client = None
            await client.aclose()
            logger.info("nojo_mcp_stopped")

    mcp = MCPServer(
        name="nojo",
        version="0.1.0",
        instructions=INSTRUCTIONS,
        lifespan=lifespan,
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=settings.issuer_url,
            resource_server_url=settings.resource_server_url,
        ),
    )
    register_tools(mcp)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> Response:
        return JSONResponse({"status": "ok"})

    return mcp
