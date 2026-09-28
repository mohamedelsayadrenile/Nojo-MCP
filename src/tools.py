import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Literal

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field

from src.core.config import Settings
from src.helpers import crop_options, farms_and_crops
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

_IDEMPOTENT_WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)

_NAME_MIN, _NAME_MAX = 2, 50
_Name = Annotated[str, Field(min_length=_NAME_MIN, max_length=_NAME_MAX)]
_FarmType = Literal["Open Field", "Greenhouse"]
_Latitude = Annotated[float, Field(ge=-90, le=90)]
_Longitude = Annotated[float, Field(ge=-180, le=180)]


def _clean_name(name: str) -> str:
    name = name.strip()
    if not _NAME_MIN <= len(name) <= _NAME_MAX:
        raise ToolError(
            f"The farm name must be {_NAME_MIN}-{_NAME_MAX} characters. "
            "Ask the user for a different name."
        )
    return name


def _name_taken(name: str) -> ToolError:
    return ToolError(
        f"A farm named '{name}' already exists. Ask the user to choose a "
        "different name."
    )


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


async def get_crop_options(ctx: ServerContext) -> dict[str, Any]:
    caller = _caller()
    state = ctx.request_context.lifespan_context
    logger.info("crop_options_requested sub=%s", caller.subject)
    return await crop_options.get_crop_options(
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


async def delete_crop(ctx: ServerContext, crop_id: str) -> dict[str, Any]:
    caller = _caller()
    crop_id = crop_id.strip()
    if not crop_id:
        raise ToolError("crop_id is required. Get it from get_farms_and_crops_ids.")

    state = ctx.request_context.lifespan_context
    logger.info("crop_delete_requested sub=%s crop_id=%s", caller.subject, crop_id)
    result = await state.nojo_client.delete(
        caller.nojo_jwt, state.settings.crop_path.format(crop_id=crop_id)
    )
    logger.info("crop_deleted sub=%s crop_id=%s", caller.subject, crop_id)
    message = result.get("message") if isinstance(result, dict) else None
    return {"deleted": True, "crop_id": crop_id, "message": message}


_ALIAS_MIN, _ALIAS_MAX = 2, 50
_ALIAS_CHARS = re.compile(r"[\w \-]+")
_AREA_TO_M2 = {"m²": 1, "feddan": 4200, "ha": 10000}
_AREA_MIN_M2, _AREA_MAX_M2 = 1, 100_000_000


def _required_id(value: str, name: str, source: str) -> str:
    value = value.strip()
    if not value:
        raise ToolError(f"{name} is required. Get it from {source}.")
    return value


def _clean_alias(name: str) -> str:
    name = name.strip()
    if (
        not _ALIAS_MIN <= len(name) <= _ALIAS_MAX
        or not _ALIAS_CHARS.fullmatch(name)
        or not any(char.isalpha() for char in name)
    ):
        raise ToolError(
            f"The crop name must be {_ALIAS_MIN}-{_ALIAS_MAX} characters of letters, "
            "numbers, spaces, '_' or '-', with at least one letter. Ask the user "
            "for a different name."
        )
    return name


_LandArea = Annotated[float, Field(gt=0)]
_LandAreaUnit = Literal["m²", "feddan", "ha"]


def _check_planting_date(planting_date: date) -> None:
    if planting_date > date.today():
        raise ToolError(
            "The planting date can't be in the future. Ask the user for the date "
            "the crop was planted."
        )


def _check_land_area(land_area: float, land_area_unit: str) -> None:
    if not _AREA_MIN_M2 <= land_area * _AREA_TO_M2[land_area_unit] <= _AREA_MAX_M2:
        raise ToolError(
            "The land area must be between 1 m² and 100,000,000 m² "
            "(1 feddan = 4,200 m², 1 ha = 10,000 m²). Ask the user to correct it."
        )


def _crop_rejected(exc: NojoAPIRequestError) -> ToolError:
    return ToolError(
        f"Nojo rejected the crop: {exc.detail or 'invalid input'}. Tell the "
        "user and ask them to correct it."
    )


async def create_crop(
    ctx: ServerContext,
    farm_id: str,
    crop_type_id: str,
    alias_crop_name: str,
    planting_date: date,
    soil_type_id: str,
    irrigation_system_id: str,
    land_area: _LandArea,
    land_area_unit: _LandAreaUnit,
) -> Any:
    caller = _caller()
    farm_id = _required_id(farm_id, "farm_id", "get_farms_and_crops_ids")
    crop_type_id = _required_id(crop_type_id, "crop_type_id", "get_crop_options")
    soil_type_id = _required_id(soil_type_id, "soil_type_id", "get_crop_options")
    irrigation_system_id = _required_id(
        irrigation_system_id, "irrigation_system_id", "get_crop_options"
    )
    alias_crop_name = _clean_alias(alias_crop_name)
    _check_planting_date(planting_date)
    _check_land_area(land_area, land_area_unit)

    state = ctx.request_context.lifespan_context
    body = {
        "farmId": farm_id,
        "cropTypeId": crop_type_id,
        "aliasCropName": alias_crop_name,
        "plantingDate": planting_date.isoformat(),
        "soilTypeId": soil_type_id,
        "irrigationSystemId": irrigation_system_id,
        "landArea": land_area,
        "landAreaUnit": land_area_unit,
    }
    logger.info("crop_create_requested sub=%s farm_id=%s", caller.subject, farm_id)
    try:
        crop = await state.nojo_client.post(
            caller.nojo_jwt, state.settings.crops_path, body
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise _crop_rejected(exc) from exc
        raise

    crop_id = crop.get("id") if isinstance(crop, dict) else None
    logger.info(
        "crop_created sub=%s farm_id=%s crop_id=%s", caller.subject, farm_id, crop_id
    )
    return crop


async def edit_crop(
    ctx: ServerContext,
    crop_id: str,
    alias_crop_name: str | None = None,
    planting_date: date | None = None,
    soil_type_id: str | None = None,
    irrigation_system_id: str | None = None,
    land_area: _LandArea | None = None,
    land_area_unit: _LandAreaUnit | None = None,
) -> Any:
    caller = _caller()
    crop_id = _required_id(crop_id, "crop_id", "get_farms_and_crops_ids")
    if (land_area is None) != (land_area_unit is None):
        raise ToolError("land_area and land_area_unit must be changed together.")

    body: dict[str, Any] = {}
    if alias_crop_name is not None:
        body["aliasCropName"] = _clean_alias(alias_crop_name)
    if planting_date is not None:
        _check_planting_date(planting_date)
        body["plantingDate"] = planting_date.isoformat()
    if soil_type_id is not None:
        body["soilTypeId"] = _required_id(
            soil_type_id, "soil_type_id", "get_crop_options"
        )
    if irrigation_system_id is not None:
        body["irrigationSystemId"] = _required_id(
            irrigation_system_id, "irrigation_system_id", "get_crop_options"
        )
    if land_area is not None and land_area_unit is not None:
        _check_land_area(land_area, land_area_unit)
        body["landArea"] = land_area
        body["landAreaUnit"] = land_area_unit
    if not body:
        raise ToolError(
            "Nothing to change. Pass at least one of alias_crop_name, "
            "planting_date, soil_type_id, irrigation_system_id, or "
            "land_area/land_area_unit."
        )

    state = ctx.request_context.lifespan_context
    logger.info(
        "crop_update_requested sub=%s crop_id=%s fields=%s",
        caller.subject,
        crop_id,
        ",".join(body),
    )
    try:
        crop = await state.nojo_client.patch(
            caller.nojo_jwt, state.settings.crop_path.format(crop_id=crop_id), body
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise _crop_rejected(exc) from exc
        raise

    logger.info("crop_updated sub=%s crop_id=%s", caller.subject, crop_id)
    return crop


async def add_farm(
    ctx: ServerContext,
    name: _Name,
    farm_type: _FarmType,
    latitude: _Latitude,
    longitude: _Longitude,
) -> Any:
    caller = _caller()
    name = _clean_name(name)

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
            raise _name_taken(name) from exc
        raise

    farm_id = farm.get("id") if isinstance(farm, dict) else None
    logger.info("farm_created sub=%s farm_id=%s", caller.subject, farm_id)
    return farm


async def edit_farm(
    ctx: ServerContext,
    farm_id: str,
    name: _Name | None = None,
    farm_type: _FarmType | None = None,
    latitude: _Latitude | None = None,
    longitude: _Longitude | None = None,
) -> Any:
    caller = _caller()
    farm_id = farm_id.strip()
    if not farm_id:
        raise ToolError("farm_id is required. Get it from get_farms_and_crops_ids.")
    if (latitude is None) != (longitude is None):
        raise ToolError("latitude and longitude must be changed together.")

    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name = _clean_name(name)
    if farm_type is not None:
        body["farmType"] = farm_type
    if latitude is not None:
        body["latitude"] = latitude
        body["longitude"] = longitude
    if not body:
        raise ToolError(
            "Nothing to change. Pass at least one of name, farm_type, or "
            "latitude/longitude."
        )

    state = ctx.request_context.lifespan_context
    logger.info(
        "farm_update_requested sub=%s farm_id=%s fields=%s",
        caller.subject,
        farm_id,
        ",".join(body),
    )
    try:
        farm = await state.nojo_client.patch(
            caller.nojo_jwt, state.settings.farm_path.format(farm_id=farm_id), body
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400 and name is not None:
            raise _name_taken(name) from exc
        raise

    logger.info("farm_updated sub=%s farm_id=%s", caller.subject, farm_id)
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
    get_crop_options: (
        "List the crop types, soil types, and irrigation systems a new crop can "
        "use, as names and ids only.\n\n"
        'Returns {"cropTypes": [{"cropId": str, "cropName": str, "cropNameAr": '
        'str}], "soilTypes": [{"soilId": str, "soilName": str}], '
        '"irrigationSystems": [{"irrigationId": str, "irrigationName": str}]}.\n'
        "Call this when adding or editing a crop to turn the user's crop type, soil "
        "type, and irrigation system into ids. Match the user's words loosely: "
        "accept typos and spelling variants, and compare crop types against both "
        "cropName and cropNameAr. If a choice is not in these lists, refuse: tell "
        "the user it is not available and show the available options. Never "
        "invent an id."
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


_DELETE_CROP_DESCRIPTION = (
    "Permanently delete one crop from one of the authenticated farmer's farms.\n\n"
    "`crop_id` must be a cropId returned by get_farms_and_crops_ids. Match the "
    "crop the user named against both cropName and cropNameAr loosely (accept "
    "typos and spelling variants); if the user named a farm, look only in that "
    "farm. If the crop exists on more than one farm, ask the user which farm. If "
    "nothing matches, tell the user and list their crops with each crop's farm. "
    "Before calling, always ask the user to confirm, naming the crop and its farm "
    "(e.g. 'Delete Avocado from North Field?'), and call only after they agree.\n"
    'Returns {"deleted": true, "crop_id": str, "message": str}.'
)


_CROP_INPUT_RULES = (
    f"- alias_crop_name: the farmer's own name for this crop, {_ALIAS_MIN}-"
    f"{_ALIAS_MAX} characters of letters, numbers, spaces, '_' or '-', with at "
    "least one letter, not already used on the same farm.\n"
    "- planting_date: YYYY-MM-DD, not in the future.\n"
    "- land_area and land_area_unit ('m²', 'feddan', or 'ha'): the area must be "
    "between 1 m² and 100,000,000 m² once converted.\n"
)

_CREATE_CROP_DESCRIPTION = (
    "Add a new crop to one of the authenticated farmer's farms.\n\n"
    "Resolve the ids first; never invent one:\n"
    "- farm_id: a farmId from get_farms_and_crops_ids, matching the farm the "
    "user named loosely (accept typos). If nothing matches, tell the user and "
    "list their farms.\n"
    "- crop_type_id (cropId), soil_type_id (soilId), irrigation_system_id "
    "(irrigationId): from get_crop_options. If the user's crop type, soil type, "
    "or irrigation system is not in those lists, refuse: tell the user it is not "
    "available and show the available options.\n"
    "Ask the user for the rest and never guess them:\n"
    + _CROP_INPUT_RULES
    + "If the call is rejected, tell the user the reason and ask them to correct "
    "it.\n"
    "Returns the created crop, including its id."
)

_EDIT_CROP_DESCRIPTION = (
    "Change one or more details of one of the authenticated farmer's existing "
    "crops: its name, planting date, soil type, irrigation system, or land "
    "area.\n\n"
    "`crop_id` must be a cropId returned by get_farms_and_crops_ids. Match the "
    "crop the user named against both cropName and cropNameAr loosely (accept "
    "typos and spelling variants); if the user named a farm, look only in that "
    "farm. If the crop exists on more than one farm, ask the user which farm. If "
    "nothing matches, tell the user and list their crops with each crop's farm.\n"
    "A new soil_type_id (soilId) or irrigation_system_id (irrigationId) must come "
    "from get_crop_options. If the user's soil type or irrigation system is not "
    "in those lists, refuse: tell the user it is not available and show the "
    "available options.\n"
    "The crop type itself cannot be changed. If the user asks to, explain that "
    "and suggest deleting the crop and adding a new one.\n"
    "Pass only the fields the user wants to change and do not ask about the "
    "others:\n"
    + _CROP_INPUT_RULES
    + "Always pass land_area and land_area_unit together.\n"
    "If the call is rejected, tell the user the reason and ask them to correct "
    "it.\n"
    "Returns the updated crop."
)


_LOCATION_RULES = (
    "- latitude / longitude: ask the user only for the farm's location, in any "
    "form they like, as long as it includes at least the governorate or city "
    "name. Do not mention coordinates to the user. Convert the location to "
    "decimal degrees yourself and use them directly; never show them or ask the "
    "user to confirm them. Only if you cannot recognize the location, ask the "
    "user to enter just the city name.\n"
)

_ADD_FARM_DESCRIPTION = (
    "Create a new farm for the authenticated farmer.\n\n"
    "All four inputs are required; ask the user for any that are missing and "
    "never guess them:\n"
    f"- name: {_NAME_MIN}-{_NAME_MAX} characters.\n"
    "- farm_type: exactly 'Open Field' or 'Greenhouse'.\n"
    + _LOCATION_RULES
    + "If the call fails because the name already exists, tell the user and ask "
    "for another name.\n"
    "Returns the created farm, including its id."
)

_EDIT_FARM_DESCRIPTION = (
    "Change one or more details of one of the authenticated farmer's existing "
    "farms: its name, type, or location.\n\n"
    "`farm_id` must be a farmId returned by get_farms_and_crops_ids: match the "
    "farm the user named against that list loosely (accept typos and spelling "
    "variants). If nothing matches, tell the user and list their farms.\n"
    "Pass only the fields the user wants to change and do not ask about the "
    "others:\n"
    f"- name: {_NAME_MIN}-{_NAME_MAX} characters.\n"
    "- farm_type: exactly 'Open Field' or 'Greenhouse'.\n"
    + _LOCATION_RULES
    + "Always pass latitude and longitude together.\n"
    "If the call fails because the new name already exists, tell the user and "
    "ask for another name.\n"
    "Returns the updated farm."
)


def register_tools(mcp: MCPServer[AppState]) -> None:
    for tool, description in _DESCRIPTIONS.items():
        mcp.tool(annotations=_READ_ONLY, description=description)(tool)
    mcp.tool(annotations=_DESTRUCTIVE, description=_DELETE_FARM_DESCRIPTION)(
        delete_farm
    )
    mcp.tool(annotations=_CREATE, description=_ADD_FARM_DESCRIPTION)(add_farm)
    mcp.tool(annotations=_IDEMPOTENT_WRITE, description=_EDIT_FARM_DESCRIPTION)(
        edit_farm
    )
    mcp.tool(annotations=_DESTRUCTIVE, description=_DELETE_CROP_DESCRIPTION)(
        delete_crop
    )
    mcp.tool(annotations=_CREATE, description=_CREATE_CROP_DESCRIPTION)(create_crop)
    mcp.tool(annotations=_IDEMPOTENT_WRITE, description=_EDIT_CROP_DESCRIPTION)(
        edit_crop
    )
