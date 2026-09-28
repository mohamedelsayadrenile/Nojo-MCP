import json

import pytest

from tests.conftest import mcp_client, running


TOOL_PATHS = {
    "get_current_user": "/api/auth/me",
    "list_farms": "/api/farms",
    "list_crops": "/api/crops",
    "list_alerts": "/api/alerts",
    "list_stations": "/api/stations",
    "get_farms_and_crops_ids": "/api/farms/overview",
}

FARM_ID = "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
FARM_PATH = f"/api/farms/{FARM_ID}"


@pytest.mark.parametrize("tool, path", TOOL_PATHS.items())
async def test_tool_calls_the_expected_platform_endpoint(
    build_test_app, backend, tool, path
):
    backend.platform_responses[path] = (200, [{"ok": True, "path": path}])
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
    backend.platform_responses[path] = (200, [])
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


async def test_delete_farm_sends_delete_with_the_exchanged_jwt(build_test_app, backend):
    backend.platform_responses[FARM_PATH] = (200, {"message": "Farm deleted successfully"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("delete_farm", {"farm_id": f"  {FARM_ID} "})

    assert not result.is_error
    assert json.loads(result.content[0].text) == {
        "deleted": True,
        "farm_id": FARM_ID,
        "message": "Farm deleted successfully",
    }
    request = backend.platform_requests[0]
    assert request.method == "DELETE"
    assert request.url.path == FARM_PATH
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"


async def test_delete_farm_not_found_is_a_tool_error(build_test_app, backend):
    backend.platform_responses[FARM_PATH] = (404, {"message": "Farm not found"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("delete_farm", {"farm_id": FARM_ID})

    assert result.is_error


async def test_delete_farm_rejects_a_blank_id_without_calling_the_api(
    build_test_app, backend
):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("delete_farm", {"farm_id": "   "})

    assert result.is_error
    assert backend.platform_requests == []


async def test_delete_farm_is_marked_destructive(build_test_app, backend):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    annotations = tools["delete_farm"].annotations
    assert annotations.destructive_hint is True
    assert annotations.read_only_hint is False
    assert tools["get_farms_and_crops_ids"].annotations.read_only_hint is True


CREATED_FARM = {
    "id": FARM_ID,
    "name": "North Field",
    "farmType": "Greenhouse",
    "latitude": 30.0444,
    "longitude": 31.2357,
}
ADD_FARM_ARGS = {
    "name": "  North Field ",
    "farm_type": "Greenhouse",
    "latitude": 30.0444,
    "longitude": 31.2357,
}


async def test_add_farm_posts_exactly_the_four_fields(build_test_app, backend):
    backend.platform_responses["/api/farms"] = (201, CREATED_FARM)
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("add_farm", ADD_FARM_ARGS)

    assert not result.is_error
    assert json.loads(result.content[0].text) == CREATED_FARM
    request = backend.platform_requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/farms"
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"
    assert json.loads(request.content) == {
        "name": "North Field",
        "farmType": "Greenhouse",
        "latitude": 30.0444,
        "longitude": 31.2357,
    }


async def test_add_farm_400_means_the_name_already_exists(build_test_app, backend):
    backend.platform_responses["/api/farms"] = (400, {"message": "exists"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("add_farm", ADD_FARM_ARGS)

    assert result.is_error
    assert "already exists" in result.content[0].text


async def test_add_farm_other_backend_errors_are_tool_errors(build_test_app, backend):
    backend.platform_responses["/api/farms"] = (500, {"error": "boom"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("add_farm", ADD_FARM_ARGS)

    assert result.is_error
    assert "already exists" not in result.content[0].text


@pytest.mark.parametrize(
    "override",
    [
        {"name": "A"},
        {"name": "x" * 51},
        {"name": "   A   "},
        {"farm_type": "Orchard"},
        {"latitude": 91},
        {"longitude": -181},
    ],
)
async def test_add_farm_rejects_invalid_input_without_calling_the_api(
    build_test_app, backend, override
):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("add_farm", {**ADD_FARM_ARGS, **override})

    assert result.is_error
    assert backend.platform_requests == []
