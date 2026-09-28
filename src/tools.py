import logging
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field

from src.core.config import Settings
from src.helpers import farms_and_crops
from src.services.auth import NojoAccessToken
from src.services.errors import NojoAPIRequestError
from src.services.nojo_client import NojoClient

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    nojo_client: NojoClient
    settings: Settings


ServerContext = Context[AppState, Any]

_READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)
_DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)
_CREATE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)

_NAME_MIN, _NAME_MAX = 2, 50


def _caller() -> NojoAccessToken:
    access_token = get_access_token()
    if not isinstance(access_token, NojoAccessToken):  # pragma: no cover
        raise ToolError(
            "No Nojo credentials on this request. Ask the user to reconnect "
            "the Nojo connector."
        )
    return access_token


async def _fetch(ctx: ServerContext, path: str) -> Any:
    caller = _caller()
    logger.info("nojo_api_called path=%s sub=%s", path, caller.subject)
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.get(caller.nojo_jwt, path)


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
    return await _fetch(ctx, "/auth/me")


async def list_farms(ctx: ServerContext) -> Any:
    return await _fetch(ctx, "/farms")


async def list_crops(ctx: ServerContext) -> Any:
    return await _fetch(ctx, "/crops")


async def list_alerts(ctx: ServerContext) -> Any:
    return await _fetch(ctx, "/alerts")


async def list_stations(ctx: ServerContext) -> Any:
    return await _fetch(ctx, "/stations")


async def get_farms_and_crops_ids(ctx: ServerContext) -> list[dict[str, Any]]:
    caller = _caller()
    state = ctx.request_context.lifespan_context
    logger.info("farms_overview_requested sub=%s", caller.subject)
    return await farms_and_crops.get_farms_and_crops_ids(
        state.nojo_client, state.settings, caller.nojo_jwt
    )


async def delete_farm(ctx: ServerContext, farm_id: str) -> dict[str, Any]:
    caller = _caller()
    farm_id = farm_id.strip()
    if not farm_id:
        raise ToolError(
            "farm_id is required. Get it from get_farms_and_crops_ids."
        )

    state = ctx.request_context.lifespan_context
    logger.info("farm_delete_requested sub=%s farm_id=%s", caller.subject, farm_id)
    result = await state.nojo_client.delete(
        caller.nojo_jwt, state.settings.farm_path.format(farm_id=farm_id)
    )
    logger.info("farm_deleted sub=%s farm_id=%s", caller.subject, farm_id)
    message = result.get("message") if isinstance(result, dict) else None
    return {"deleted": True, "farm_id": farm_id, "message": message}


async def add_farm(
    ctx: ServerContext,
    name: Annotated[str, Field(min_length=_NAME_MIN, max_length=_NAME_MAX)],
    farm_type: Literal["Open Field", "Greenhouse"],
    latitude: Annotated[float, Field(ge=-90, le=90)],
    longitude: Annotated[float, Field(ge=-180, le=180)],
) -> Any:
    caller = _caller()
    name = name.strip()
    if not _NAME_MIN <= len(name) <= _NAME_MAX:
        raise ToolError(
            f"The farm name must be {_NAME_MIN}-{_NAME_MAX} characters. "
            "Ask the user for a different name."
        )

    state = ctx.request_context.lifespan_context
    body = {
        "name": name,
        "farmType": farm_type,
        "latitude": latitude,
        "longitude": longitude,
    }
    logger.info("farm_create_requested sub=%s farm_type=%s", caller.subject, farm_type)
    try:
        farm = await state.nojo_client.post(
            caller.nojo_jwt, state.settings.farms_path, body
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise ToolError(
                f"A farm named '{name}' already exists. Ask the user to choose a "
                "different name."
            ) from exc
        raise

    farm_id = farm.get("id") if isinstance(farm, dict) else None
    logger.info("farm_created sub=%s farm_id=%s", caller.subject, farm_id)
    return farm


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
    get_farms_and_crops_ids: (
        "List the authenticated farmer's farms and the crops on each, as names "
        "and ids only.\n\n"
        'Returns [{"farmId": str, "farmName": str, "crops": [{"cropId": str, '
        '"cropName": str, "cropNameAr": str}]}].\n'
        "Call this whenever the user refers to a farm or crop by name and another "
        "tool needs its id. Match the user's words to these names loosely: accept "
        "typos and spelling variants (e.g. 'mohammed farm' matches 'Mohamed Farm'), "
        "ignore case and a trailing 'farm', and compare crops against both cropName "
        "and cropNameAr. If nothing reasonably matches, tell the user no farm or "
        "crop with that name exists and list the available names. If several could "
        "match, ask the user which one they mean. Never invent an id."
    ),
}


_DELETE_FARM_DESCRIPTION = (
    "Permanently delete one of the authenticated farmer's farms. All crops on it "
    "are removed and its linked devices are freed.\n\n"
    "`farm_id` must be a farmId returned by get_farms_and_crops_ids: resolve the "
    "farm the user named with that tool first. Before calling, always ask the user "
    "to confirm, naming the exact farm (e.g. 'Delete Mohamed Farm and all its "
    "crops?'), and call only after they agree.\n"
    'Returns {"deleted": true, "farm_id": str, "message": str}.'
)


_ADD_FARM_DESCRIPTION = (
    "Create a new farm for the authenticated farmer.\n\n"
    "All four inputs are required; ask the user for any that are missing and "
    "never guess them:\n"
    f"- name: {_NAME_MIN}-{_NAME_MAX} characters.\n"
    "- farm_type: exactly 'Open Field' or 'Greenhouse'.\n"
    "- latitude / longitude: ask the user to type the farm's location (city, "
    "village, or address), then convert it yourself to decimal degrees. If the "
    "place is ambiguous, confirm it with the user first.\n"
    "If the call fails because the name already exists, tell the user and ask "
    "for another name.\n"
    "Returns the created farm, including its id."
)


def register_tools(mcp: MCPServer[AppState]) -> None:
    for tool, description in _DESCRIPTIONS.items():
        mcp.tool(annotations=_READ_ONLY, description=description)(tool)
    mcp.tool(annotations=_DESTRUCTIVE, description=_DELETE_FARM_DESCRIPTION)(
        delete_farm
    )
    mcp.tool(annotations=_CREATE, description=_ADD_FARM_DESCRIPTION)(add_farm)
