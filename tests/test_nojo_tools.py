import json

import pytest

from tests.conftest import mcp_client, running


TOOL_PATHS = {
    "get_current_user": "/api/auth/me",
    "list_farms": "/api/farms",
    "list_crops": "/api/crops",
    "list_alerts": "/api/alerts",
    "list_stations": "/api/stations",
}


@pytest.mark.parametrize("tool, path", TOOL_PATHS.items())
async def test_tool_calls_the_expected_platform_endpoint(
    build_test_app, backend, tool, path
):
    backend.platform_responses[path] = (200, {"ok": True, "path": path})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {})

    assert not result.is_error
    assert json.loads(result.content[0].text) == {"ok": True, "path": path}
    assert backend.platform_requests[0].url.path == path


@pytest.mark.parametrize("tool, path", TOOL_PATHS.items())
async def test_tool_sends_the_exchanged_jwt_not_the_oauth_token(
    build_test_app, backend, tool, path
):
    backend.platform_responses[path] = (200, {})
    oauth_token = backend.grant("alice")
    app = build_test_app()
    async with running(app), mcp_client(app, oauth_token) as client:
        await client.call_tool(tool, {})

    auth_header = backend.platform_requests[0].headers["authorization"]
    assert auth_header == "Bearer nojo-jwt-alice"
    assert oauth_token not in auth_header


@pytest.mark.parametrize("tool, path", TOOL_PATHS.items())
async def test_a_non_200_platform_response_is_a_tool_error(
    build_test_app, backend, tool, path
):
    backend.platform_responses[path] = (500, {"error": "boom"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {})

    assert result.is_error
