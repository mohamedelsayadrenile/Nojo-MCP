import json
from datetime import date, timedelta

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


async def _edit(build_test_app, backend, args):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        return await client.call_tool("edit_farm", {"farm_id": FARM_ID, **args})


@pytest.mark.parametrize(
    "args, body",
    [
        ({"name": "  Alpha "}, {"name": "Alpha"}),
        ({"farm_type": "Open Field"}, {"farmType": "Open Field"}),
        (
            {"latitude": 30.0131, "longitude": 31.2089},
            {"latitude": 30.0131, "longitude": 31.2089},
        ),
    ],
)
async def test_edit_farm_patches_only_the_changed_fields(
    build_test_app, backend, args, body
):
    backend.platform_responses[FARM_PATH] = (200, CREATED_FARM)
    result = await _edit(build_test_app, backend, args)

    assert not result.is_error
    assert json.loads(result.content[0].text) == CREATED_FARM
    request = backend.platform_requests[0]
    assert request.method == "PATCH"
    assert request.url.path == FARM_PATH
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"
    assert json.loads(request.content) == body


async def test_edit_farm_400_on_rename_means_the_name_already_exists(
    build_test_app, backend
):
    backend.platform_responses[FARM_PATH] = (400, {"message": "exists"})
    result = await _edit(build_test_app, backend, {"name": "Alpha"})

    assert result.is_error
    assert "already exists" in result.content[0].text


async def test_edit_farm_400_without_a_name_is_not_a_name_clash(
    build_test_app, backend
):
    backend.platform_responses[FARM_PATH] = (400, {"message": "Invalid body"})
    result = await _edit(build_test_app, backend, {"farm_type": "Greenhouse"})

    assert result.is_error
    assert "already exists" not in result.content[0].text


async def test_edit_farm_not_found_is_a_tool_error(build_test_app, backend):
    backend.platform_responses[FARM_PATH] = (404, {"message": "Farm not found"})
    result = await _edit(build_test_app, backend, {"name": "Alpha"})

    assert result.is_error


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"latitude": 30.0},
        {"farm_id": "  ", "name": "Alpha"},
        {"name": "A"},
        {"farm_type": "Orchard"},
    ],
)
async def test_edit_farm_rejects_invalid_input_without_calling_the_api(
    build_test_app, backend, args
):
    result = await _edit(build_test_app, backend, args)

    assert result.is_error
    assert backend.platform_requests == []


CROP_ID = "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
CROP_PATH = f"/api/crops/{CROP_ID}"


async def test_delete_crop_sends_delete_with_the_exchanged_jwt(build_test_app, backend):
    backend.platform_responses[CROP_PATH] = (200, {"message": "Crop deleted successfully"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("delete_crop", {"crop_id": f" {CROP_ID}  "})

    assert not result.is_error
    assert json.loads(result.content[0].text) == {
        "deleted": True,
        "crop_id": CROP_ID,
        "message": "Crop deleted successfully",
    }
    request = backend.platform_requests[0]
    assert request.method == "DELETE"
    assert request.url.path == CROP_PATH
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"


async def test_delete_crop_not_found_is_a_tool_error(build_test_app, backend):
    backend.platform_responses[CROP_PATH] = (404, {"message": "Crop not found"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("delete_crop", {"crop_id": CROP_ID})

    assert result.is_error


async def test_delete_crop_rejects_a_blank_id_without_calling_the_api(
    build_test_app, backend
):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("delete_crop", {"crop_id": "  "})

    assert result.is_error
    assert backend.platform_requests == []


async def test_delete_crop_is_marked_destructive(build_test_app, backend):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert tools["delete_crop"].annotations.destructive_hint is True


CROP_OPTIONS = {
    "cropTypes": [{"cropId": "c-1", "cropName": "Wheat", "cropNameAr": "قمح"}],
    "soilTypes": [{"soilId": "s-1", "soilName": "Clay"}],
    "irrigationSystems": [{"irrigationId": "i-1", "irrigationName": "Drip"}],
}


async def test_get_crop_options_returns_the_options(build_test_app, backend):
    backend.platform_responses["/api/crops/options"] = (200, CROP_OPTIONS)
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("get_crop_options", {})

    assert not result.is_error
    assert json.loads(result.content[0].text) == CROP_OPTIONS
    assert backend.platform_requests[0].headers["authorization"] == (
        "Bearer nojo-jwt-alice"
    )


async def test_get_crop_options_backend_error_is_a_tool_error(build_test_app, backend):
    backend.platform_responses["/api/crops/options"] = (500, {"error": "boom"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("get_crop_options", {})

    assert result.is_error


CREATE_CROP_ARGS = {
    "farm_id": FARM_ID,
    "crop_type_id": "c-1",
    "alias_crop_name": "  Wheat 1 ",
    "planting_date": "2026-03-15",
    "soil_type_id": "s-1",
    "irrigation_system_id": "i-1",
    "land_area": 2.5,
    "land_area_unit": "feddan",
}
CREATED_CROP = {"id": CROP_ID, "farmId": FARM_ID, "cropTypeName": "Wheat"}


async def _create_crop(build_test_app, backend, args):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        return await client.call_tool("create_crop", args)


async def test_create_crop_posts_exactly_the_documented_fields(
    build_test_app, backend
):
    backend.platform_responses["/api/crops"] = (201, CREATED_CROP)
    result = await _create_crop(build_test_app, backend, CREATE_CROP_ARGS)

    assert not result.is_error
    assert json.loads(result.content[0].text) == CREATED_CROP
    request = backend.platform_requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/crops"
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"
    assert json.loads(request.content) == {
        "farmId": FARM_ID,
        "cropTypeId": "c-1",
        "aliasCropName": "Wheat 1",
        "plantingDate": "2026-03-15",
        "soilTypeId": "s-1",
        "irrigationSystemId": "i-1",
        "landArea": 2.5,
        "landAreaUnit": "feddan",
    }


async def test_create_crop_400_relays_the_backend_reason(build_test_app, backend):
    backend.platform_responses["/api/crops"] = (
        400,
        {"message": "aliasCropName already used on this farm"},
    )
    result = await _create_crop(build_test_app, backend, CREATE_CROP_ARGS)

    assert result.is_error
    assert "aliasCropName already used on this farm" in result.content[0].text


@pytest.mark.parametrize(
    "override",
    [
        {"alias_crop_name": "W"},
        {"alias_crop_name": "123"},
        {"alias_crop_name": "Wheat!"},
        {"alias_crop_name": "x" * 51},
        {"planting_date": (date.today() + timedelta(days=1)).isoformat()},
        {"planting_date": "15-03-2026"},
        {"land_area": 0},
        {"land_area": 0.0001, "land_area_unit": "m²"},
        {"land_area": 30000, "land_area_unit": "feddan"},
        {"land_area_unit": "acre"},
        {"farm_id": "  "},
        {"soil_type_id": ""},
    ],
)
async def test_create_crop_rejects_invalid_input_without_calling_the_api(
    build_test_app, backend, override
):
    result = await _create_crop(build_test_app, backend, {**CREATE_CROP_ARGS, **override})

    assert result.is_error
    assert backend.platform_requests == []


async def _edit_crop(build_test_app, backend, args):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        return await client.call_tool("edit_crop", {"crop_id": CROP_ID, **args})


@pytest.mark.parametrize(
    "args, body",
    [
        ({"alias_crop_name": " North Wheat "}, {"aliasCropName": "North Wheat"}),
        ({"irrigation_system_id": " i-2 "}, {"irrigationSystemId": "i-2"}),
        ({"soil_type_id": "s-2"}, {"soilTypeId": "s-2"}),
        (
            {"land_area": 3, "land_area_unit": "ha"},
            {"landArea": 3, "landAreaUnit": "ha"},
        ),
        ({"planting_date": "2026-04-01"}, {"plantingDate": "2026-04-01"}),
    ],
)
async def test_edit_crop_patches_only_the_changed_fields(
    build_test_app, backend, args, body
):
    backend.platform_responses[CROP_PATH] = (200, CREATED_CROP)
    result = await _edit_crop(build_test_app, backend, args)

    assert not result.is_error
    assert json.loads(result.content[0].text) == CREATED_CROP
    request = backend.platform_requests[0]
    assert request.method == "PATCH"
    assert request.url.path == CROP_PATH
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"
    assert json.loads(request.content) == body


async def test_edit_crop_400_relays_the_backend_reason(build_test_app, backend):
    backend.platform_responses[CROP_PATH] = (400, {"message": "Unknown soil type"})
    result = await _edit_crop(build_test_app, backend, {"soil_type_id": "s-9"})

    assert result.is_error
    assert "Unknown soil type" in result.content[0].text


async def test_edit_crop_not_found_is_a_tool_error(build_test_app, backend):
    backend.platform_responses[CROP_PATH] = (404, {"message": "Crop not found"})
    result = await _edit_crop(build_test_app, backend, {"alias_crop_name": "Wheat"})

    assert result.is_error


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"land_area": 2},
        {"land_area_unit": "ha"},
        {"planting_date": (date.today() + timedelta(days=1)).isoformat()},
        {"alias_crop_name": "123"},
        {"land_area": 0.5, "land_area_unit": "m²"},
        {"crop_id": "  ", "alias_crop_name": "Wheat"},
        {"soil_type_id": ""},
    ],
)
async def test_edit_crop_rejects_invalid_input_without_calling_the_api(
    build_test_app, backend, args
):
    result = await _edit_crop(build_test_app, backend, args)

    assert result.is_error
    assert backend.platform_requests == []


FARM_SCOPED_TOOLS = {
    "get_current_weather": ("/api/weather/overview", {}),
    "get_forecasting_weather": ("/api/weather/overview/forecast", {}),
    "get_past_weather": ("/api/weather/overview/history", {"days": "7"}),
    "get_current_irrigation": ("/api/irrigation/overview", {}),
    "get_past_irrigation": ("/api/irrigation/overview/history", {"days": "7"}),
    "get_current_alerts": ("/api/alerts/overview", {}),
    "get_past_alerts": ("/api/alerts/overview/history", {}),
    "get_current_vpd": ("/api/agronomy/vpd/overview", {}),
    "get_past_vpd": ("/api/agronomy/vpd/overview/history", {"days": "1"}),
}
PAST_TOOLS = {
    "get_past_weather": "/api/weather/overview/history",
    "get_past_irrigation": "/api/irrigation/overview/history",
    "get_past_vpd": "/api/agronomy/vpd/overview/history",
}


@pytest.mark.parametrize(
    "tool, path, query", [(k, *v) for k, v in FARM_SCOPED_TOOLS.items()]
)
async def test_farm_data_for_all_farms_sends_no_farm_id(
    build_test_app, backend, tool, path, query
):
    backend.platform_responses[path] = (200, [{"farmId": FARM_ID}])
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {})

    assert not result.is_error
    assert json.loads(result.content[0].text) == {"farmId": FARM_ID}
    request = backend.platform_requests[0]
    assert request.method == "GET"
    assert request.url.path == path
    assert dict(request.url.params) == query
    assert request.headers["authorization"] == "Bearer nojo-jwt-alice"


@pytest.mark.parametrize(
    "tool, path, query", [(k, *v) for k, v in FARM_SCOPED_TOOLS.items()]
)
async def test_farm_data_for_one_farm_sends_its_farm_id(
    build_test_app, backend, tool, path, query
):
    row = {"farmId": FARM_ID, "farmName": "North Farm"}
    backend.platform_responses[path] = (200, row)
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {"farm_id": f" {FARM_ID} "})

    assert not result.is_error
    assert json.loads(result.content[0].text) == row
    assert dict(backend.platform_requests[0].url.params) == {**query, "farmId": FARM_ID}


@pytest.mark.parametrize("tool, path", [(k, v[0]) for k, v in FARM_SCOPED_TOOLS.items()])
async def test_farm_data_unknown_farm_is_a_tool_error(
    build_test_app, backend, tool, path
):
    backend.platform_responses[path] = (404, {"message": "Farm not found"})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {"farm_id": FARM_ID})

    assert result.is_error


@pytest.mark.parametrize("tool, path", PAST_TOOLS.items())
async def test_past_tools_send_the_requested_days(build_test_app, backend, tool, path):
    backend.platform_responses[path] = (200, [])
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {"days": 3})

    assert not result.is_error
    assert dict(backend.platform_requests[0].url.params) == {"days": "3"}


@pytest.mark.parametrize("tool", PAST_TOOLS)
async def test_past_tools_reject_zero_days(build_test_app, backend, tool):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {"days": 0})

    assert result.is_error
    assert backend.platform_requests == []


@pytest.mark.parametrize("days", [8, 30])
@pytest.mark.parametrize("tool", PAST_TOOLS)
async def test_past_tools_allow_at_most_7_days(build_test_app, backend, tool, days):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(tool, {"days": days})

    assert result.is_error
    assert "Only the last 7 days" in result.content[0].text
    assert backend.platform_requests == []


@pytest.mark.parametrize("day", ["yesterday", "before-yesterday"])
async def test_past_alerts_sends_the_chosen_day(build_test_app, backend, day):
    backend.platform_responses["/api/alerts/overview/history"] = (200, {"alerts": []})
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool(
            "get_past_alerts", {"day": day, "farm_id": FARM_ID}
        )

    assert not result.is_error
    assert dict(backend.platform_requests[0].url.params) == {
        "day": day,
        "farmId": FARM_ID,
    }


async def test_past_alerts_rejects_other_days(build_test_app, backend):
    app = build_test_app()
    async with running(app), mcp_client(app, backend.grant("alice")) as client:
        result = await client.call_tool("get_past_alerts", {"day": "last-week"})

    assert result.is_error
    assert backend.platform_requests == []
