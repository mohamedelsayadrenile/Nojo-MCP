import os
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qs

ISSUER_URL = "https://auth.nojo.test"
RESOURCE_SERVER_URL = "http://testserver/mcp"
API_BASE_URL = "https://api.nojo.test/api"
TOKEN_EXCHANGE_URL = f"{ISSUER_URL}/oauth/token"
FARMS_OVERVIEW_PATH = "/farms/overview"
FARMS_PATH = "/farms"
FARM_PATH = "/farms/{farm_id}"
CROP_PATH = "/crops/{crop_id}"
CROPS_PATH = "/crops"
CROP_OPTIONS_PATH = "/crops/options"
MCP_CLIENT_ID = "nojo-mcp"
MCP_CLIENT_SECRET = "test-client-secret"

os.environ.setdefault("NOJO_ISSUER_URL", ISSUER_URL)
os.environ.setdefault("NOJO_RESOURCE_SERVER_URL", RESOURCE_SERVER_URL)
os.environ.setdefault("NOJO_API_BASE_URL", API_BASE_URL)
os.environ.setdefault("NOJO_FARMS_OVERVIEW_PATH", FARMS_OVERVIEW_PATH)
os.environ.setdefault("NOJO_FARMS_PATH", FARMS_PATH)
os.environ.setdefault("NOJO_FARM_PATH", FARM_PATH)
os.environ.setdefault("NOJO_CROP_PATH", CROP_PATH)
os.environ.setdefault("NOJO_CROPS_PATH", CROPS_PATH)
os.environ.setdefault("NOJO_CROP_OPTIONS_PATH", CROP_OPTIONS_PATH)
os.environ.setdefault("ALLOWED_HOSTS", "testserver")
os.environ.setdefault("TOKEN_EXCHANGE_URL", TOKEN_EXCHANGE_URL)
os.environ.setdefault("MCP_OAUTH_CLIENT_ID", MCP_CLIENT_ID)
os.environ.setdefault("MCP_OAUTH_CLIENT_SECRET", MCP_CLIENT_SECRET)

import httpx  # noqa: E402
import httpx2  # noqa: E402
import pytest  # noqa: E402
from mcp.client.client import Client  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402

from src.core.config import Settings  # noqa: E402

MCP_URL = "http://testserver/mcp"
JSON_RPC_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "http-test", "version": "1"},
    },
}


@asynccontextmanager
async def running(app):
    async with app.router.lifespan_context(app):
        yield app


def raw(app, token: str | None = None) -> httpx2.AsyncClient:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers,
    )


@asynccontextmanager
async def mcp_client(app, token: str, **kwargs):
    async with Client(
        streamable_http_client(MCP_URL, http_client=raw(app, token)), **kwargs
    ) as client:
        yield client


def make_settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "NOJO_ISSUER_URL": ISSUER_URL,
        "NOJO_RESOURCE_SERVER_URL": RESOURCE_SERVER_URL,
        "NOJO_API_BASE_URL": API_BASE_URL,
        "NOJO_FARMS_OVERVIEW_PATH": FARMS_OVERVIEW_PATH,
        "NOJO_FARMS_PATH": FARMS_PATH,
        "NOJO_FARM_PATH": FARM_PATH,
        "NOJO_CROP_PATH": CROP_PATH,
        "NOJO_CROPS_PATH": CROPS_PATH,
        "NOJO_CROP_OPTIONS_PATH": CROP_OPTIONS_PATH,
        "ALLOWED_HOSTS": ["testserver"],
        "TOKEN_EXCHANGE_URL": TOKEN_EXCHANGE_URL,
        "MCP_OAUTH_CLIENT_ID": MCP_CLIENT_ID,
        "MCP_OAUTH_CLIENT_SECRET": MCP_CLIENT_SECRET,
    }
    return Settings(_env_file=None, **{**defaults, **overrides})


class BackendRecorder:
    """Stands in for the Nojo backend's token-exchange endpoint."""

    def __init__(self) -> None:
        self.exchanges: list[httpx.Request] = []
        self.platform_requests: list[httpx.Request] = []
        self.clients: list[httpx.AsyncClient] = []
        self.exchange_status_code: int | None = None
        self.malformed = False
        self.platform_responses: dict[str, tuple[int, Any]] = {}
        self._grants: dict[str, dict[str, Any]] = {}

    def grant(self, user: str = "user-1", *, expires_in: int = 900) -> str:
        oauth_token = f"oauth-{user}"
        self._grants[oauth_token] = {
            "access_token": f"nojo-jwt-{user}",
            "expires_in": expires_in,
            "sub": user,
            "client_id": "https://claude.ai/oauth/mcp-oauth-client-metadata",
        }
        return oauth_token

    def exchange_form(self, index: int = 0) -> dict[str, str]:
        body = parse_qs(self.exchanges[index].content.decode())
        return {key: values[0] for key, values in body.items()}

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path != "/oauth/token":
            self.platform_requests.append(request)
            status, body = self.platform_responses.get(
                request.url.path, (200, {"error": "not_stubbed"})
            )
            return httpx.Response(status, json=body)

        self.exchanges.append(request)
        if self.exchange_status_code is not None:
            return httpx.Response(
                self.exchange_status_code, json={"error": "server_error"}
            )
        if self.malformed:
            return httpx.Response(200, json={"not": "a token"})
        grant = self._grants.get(parse_qs(request.content.decode())["subject_token"][0])
        if grant is None:
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(200, json=grant)


@pytest.fixture
def backend() -> BackendRecorder:
    return BackendRecorder()


@pytest.fixture
def patched_backend(
    monkeypatch: pytest.MonkeyPatch, backend: BackendRecorder
) -> Iterator[BackendRecorder]:
    import src.server as server_module

    def fake_build(settings: Settings) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            headers={"Accept": "application/json"},
            transport=httpx.MockTransport(backend.handler),
        )
        backend.clients.append(client)
        return client

    monkeypatch.setattr(server_module, "build_http_client", fake_build)
    yield backend


@pytest.fixture
def build_test_app(patched_backend: BackendRecorder) -> Callable[..., Any]:
    from src.app import build_app

    def _build(**overrides: Any):
        return build_app(make_settings(**overrides))

    return _build
