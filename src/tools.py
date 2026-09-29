import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
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


def _farm_params(farm_id: str | None) -> dict[str, str]:
    farm_id = (farm_id or "").strip()
    return {"farmId": farm_id} if farm_id else {}


_PAST_DAYS_MAX = 7
_PastDays = Annotated[int, Field(ge=1)]


def _check_past_days(days: int) -> None:
    if days > _PAST_DAYS_MAX:
        raise ToolError(
            f"Only the last {_PAST_DAYS_MAX} days are available. Tell the user and "
            f"offer the last {_PAST_DAYS_MAX} days instead."
        )


async def _farm_scoped(ctx: ServerContext, path: str, params: dict[str, Any]) -> Any:
    caller = _caller()
    logger.info(
        "farm_data_requested sub=%s path=%s farm_id=%s",
        caller.subject,
        path,
        params.get("farmId", "all"),
    )
    nojo_client = ctx.request_context.lifespan_context.nojo_client
    return await nojo_client.get(caller.nojo_jwt, path, params)


async def get_current_weather(ctx: ServerContext, farm_id: str | None = None) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.weather_current_path, _farm_params(farm_id)
    )


async def get_forecasting_weather(
    ctx: ServerContext, farm_id: str | None = None
) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.weather_forecast_path, _farm_params(farm_id)
    )


async def get_past_weather(
    ctx: ServerContext,
    days: _PastDays = _PAST_DAYS_MAX,
    farm_id: str | None = None,
) -> Any:
    _check_past_days(days)
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.weather_history_path, {"days": days, **_farm_params(farm_id)}
    )


async def get_current_irrigation(
    ctx: ServerContext, farm_id: str | None = None
) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.irrigation_current_path, _farm_params(farm_id)
    )


async def get_past_irrigation(
    ctx: ServerContext,
    days: _PastDays = _PAST_DAYS_MAX,
    farm_id: str | None = None,
) -> Any:
    _check_past_days(days)
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.irrigation_history_path, {"days": days, **_farm_params(farm_id)}
    )


async def get_current_alerts(ctx: ServerContext, farm_id: str | None = None) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(ctx, settings.alerts_current_path, _farm_params(farm_id))


async def get_past_alerts(
    ctx: ServerContext,
    day: Literal["yesterday", "before-yesterday"] | None = None,
    farm_id: str | None = None,
) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    params = {"day": day} if day else {}
    return await _farm_scoped(
        ctx, settings.alerts_history_path, {**params, **_farm_params(farm_id)}
    )


async def get_current_vpd(ctx: ServerContext, farm_id: str | None = None) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(ctx, settings.vpd_current_path, _farm_params(farm_id))


async def get_past_vpd(
    ctx: ServerContext,
    days: _PastDays = 1,
    farm_id: str | None = None,
) -> Any:
    _check_past_days(days)
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.vpd_history_path, {"days": days, **_farm_params(farm_id)}
    )


_REPORT_DAYS = 7


def _check_report_range(from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise ToolError("from_date must not be after to_date.")
    today = date.today()
    earliest = today - timedelta(days=_REPORT_DAYS - 1)
    if from_date < earliest or to_date > today:
        raise ToolError(
            f"Nojo reports cover only the last {_REPORT_DAYS} days: "
            f"{earliest.isoformat()} to {today.isoformat()} (today). Tell the user "
            "and offer that range instead."
        )


async def get_farm_report(
    ctx: ServerContext, farm_id: str, from_date: date, to_date: date
) -> Any:
    caller = _caller()
    farm_id = _required_id(farm_id, "farm_id", "get_farms_and_crops_ids")
    _check_report_range(from_date, to_date)

    state = ctx.request_context.lifespan_context
    logger.info(
        "farm_report_requested sub=%s farm_id=%s from=%s to=%s",
        caller.subject,
        farm_id,
        from_date,
        to_date,
    )
    try:
        return await state.nojo_client.get(
            caller.nojo_jwt,
            state.settings.farm_report_path.format(farm_id=farm_id),
            {"from": from_date.isoformat(), "to": to_date.isoformat()},
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise ToolError(
                f"Nojo rejected the report dates: {exc.detail or 'invalid dates'}. "
                "Tell the user and offer the last 7 days (today included) instead."
            ) from exc
        raise


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


_FEEDBACK_MIN, _FEEDBACK_MAX = 2, 1200


async def send_feedback(ctx: ServerContext, message: str) -> dict[str, Any]:
    caller = _caller()
    message = message.strip()
    if not _FEEDBACK_MIN <= len(message) <= _FEEDBACK_MAX:
        raise ToolError(
            f"The feedback must be {_FEEDBACK_MIN}-{_FEEDBACK_MAX} characters "
            f"(it is {len(message)}). Adjust it and confirm it with the user again."
        )

    state = ctx.request_context.lifespan_context
    logger.info("feedback_requested sub=%s length=%s", caller.subject, len(message))
    try:
        feedback = await state.nojo_client.post(
            caller.nojo_jwt, state.settings.feedback_path, {"message": message}
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise ToolError(
                f"Nojo rejected the feedback: {exc.detail or 'invalid message'}. "
                "Adjust it and confirm it with the user again."
            ) from exc
        raise

    feedback = feedback if isinstance(feedback, dict) else {}
    logger.info(
        "feedback_sent sub=%s feedback_id=%s", caller.subject, feedback.get("id")
    )
    return {
        "sent": True,
        "feedback_id": feedback.get("id"),
        "created_at": feedback.get("createdAt"),
    }


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


_LEDGER_LISTS = ("actions", "categories")
_LEDGER_TEXT_MAX = 100
_LedgerAmount = Annotated[float, Field(gt=0, le=9_999_999_999)]


async def get_ledger(ctx: ServerContext, farm_id: str | None = None) -> Any:
    settings = ctx.request_context.lifespan_context.settings
    return await _farm_scoped(
        ctx, settings.ledger_overview_path, _farm_params(farm_id)
    )


async def get_ledger_options(ctx: ServerContext) -> dict[str, Any]:
    caller = _caller()
    state = ctx.request_context.lifespan_context
    path = state.settings.ledger_options_path
    logger.info("ledger_options_requested sub=%s", caller.subject)
    options = await state.nojo_client.get(caller.nojo_jwt, path)
    if not isinstance(options, dict) or not all(
        isinstance(options.get(key), list) for key in _LEDGER_LISTS
    ):
        logger.warning("ledger_options_failed path=%s reason=malformed_response", path)
        raise NojoAPIRequestError(
            f"The Nojo platform API returned an unexpected response for {path}."
        )
    return options


def _entry_date(entry_date: datetime) -> str:
    if entry_date.tzinfo is None:
        entry_date = entry_date.replace(tzinfo=UTC)
    if entry_date > datetime.now(UTC):
        raise ToolError(
            "The entry date can't be in the future. Ask the user when it happened."
        )
    return entry_date.isoformat()


def _ledger_text(value: str, name: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= _LEDGER_TEXT_MAX:
        raise ToolError(
            f"{name} must be 1-{_LEDGER_TEXT_MAX} characters. Ask the user to "
            "shorten it."
        )
    return value


def _ledger_rejected(exc: NojoAPIRequestError) -> ToolError:
    return ToolError(
        f"Nojo rejected the ledger entry: {exc.detail or 'invalid input'}. Tell the "
        "user. If the crop's or the farm's cycle has ended, do not retry; "
        "otherwise ask them to correct it."
    )


def _ledger_body(
    crop_id: str | None,
    action_id: str | None,
    category_id: str | None,
    amount: float | None,
    entry_date: datetime | None,
    description: str | None,
    description_ar: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if crop_id is not None:
        body["cropId"] = _required_id(crop_id, "crop_id", "get_farms_and_crops_ids")
    if action_id is not None:
        body["actionId"] = _required_id(action_id, "action_id", "get_ledger_options")
    if category_id is not None:
        body["actionTypeId"] = _required_id(
            category_id, "category_id", "get_ledger_options"
        )
    if amount is not None:
        body["amount"] = amount
    if entry_date is not None:
        body["entryDate"] = _entry_date(entry_date)
    if description is not None:
        body["description"] = _ledger_text(description, "description")
    if description_ar is not None:
        body["descriptionAr"] = _ledger_text(description_ar, "description_ar")
    return body


async def add_ledger_entry(
    ctx: ServerContext,
    farm_id: str,
    crop_id: str,
    action_id: str,
    category_id: str,
    amount: _LedgerAmount,
    entry_date: datetime | None = None,
    description: str | None = None,
    description_ar: str | None = None,
) -> Any:
    caller = _caller()
    farm_id = _required_id(farm_id, "farm_id", "get_farms_and_crops_ids")
    body = {
        "farmId": farm_id,
        **_ledger_body(
            crop_id,
            action_id,
            category_id,
            amount,
            entry_date,
            description,
            description_ar,
        ),
    }

    state = ctx.request_context.lifespan_context
    logger.info("ledger_create_requested sub=%s farm_id=%s", caller.subject, farm_id)
    try:
        entry = await state.nojo_client.post(
            caller.nojo_jwt, state.settings.ledger_path, body
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise _ledger_rejected(exc) from exc
        raise

    entry_id = entry.get("id") if isinstance(entry, dict) else None
    logger.info(
        "ledger_entry_created sub=%s farm_id=%s entry_id=%s",
        caller.subject,
        farm_id,
        entry_id,
    )
    return entry


async def edit_ledger_entry(
    ctx: ServerContext,
    entry_id: str,
    crop_id: str | None = None,
    action_id: str | None = None,
    category_id: str | None = None,
    amount: _LedgerAmount | None = None,
    entry_date: datetime | None = None,
    description: str | None = None,
    description_ar: str | None = None,
) -> Any:
    caller = _caller()
    entry_id = _required_id(entry_id, "entry_id", "get_ledger")
    body = _ledger_body(
        crop_id, action_id, category_id, amount, entry_date, description, description_ar
    )
    if not body:
        raise ToolError(
            "Nothing to change. Pass at least one of crop_id, action_id, "
            "category_id, amount, entry_date, description, or description_ar."
        )

    state = ctx.request_context.lifespan_context
    logger.info(
        "ledger_update_requested sub=%s entry_id=%s fields=%s",
        caller.subject,
        entry_id,
        ",".join(body),
    )
    try:
        entry = await state.nojo_client.put(
            caller.nojo_jwt,
            state.settings.ledger_entry_path.format(entry_id=entry_id),
            body,
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise _ledger_rejected(exc) from exc
        raise

    logger.info("ledger_entry_updated sub=%s entry_id=%s", caller.subject, entry_id)
    return entry


async def delete_ledger_entry(ctx: ServerContext, entry_id: str) -> dict[str, Any]:
    caller = _caller()
    entry_id = _required_id(entry_id, "entry_id", "get_ledger")

    state = ctx.request_context.lifespan_context
    logger.info("ledger_delete_requested sub=%s entry_id=%s", caller.subject, entry_id)
    try:
        result = await state.nojo_client.delete(
            caller.nojo_jwt, state.settings.ledger_entry_path.format(entry_id=entry_id)
        )
    except NojoAPIRequestError as exc:
        if exc.status_code == 400:
            raise _ledger_rejected(exc) from exc
        raise

    logger.info("ledger_entry_deleted sub=%s entry_id=%s", caller.subject, entry_id)
    message = result.get("message") if isinstance(result, dict) else None
    return {"deleted": True, "entry_id": entry_id, "message": message}


_FARM_SCOPE_RULES = (
    "If the user has not said which farm (or all farms), ask them first: one "
    "specific farm, or all their farms? For one farm, resolve its farmId with "
    "get_farms_and_crops_ids, matching the name loosely (accept typos); if "
    "nothing matches, tell the user and list their farms. For all farms, omit "
    "farm_id: the result is then a list with one row per farm, otherwise a "
    "single row.\n"
    "A null value, or an empty list, means there is no data: tell the user so "
    "and never guess."
)

_WEATHER_RULES = (
    _FARM_SCOPE_RULES
    + "\nGreenhouse farms have no wind or rain values. `source` is 'device' (the "
    "farm's own device) or 'model' (weather forecast model)."
)

def _past_days_rules(default: int) -> str:
    return (
        f"`days` is how many days back, 1-{_PAST_DAYS_MAX} (1 = yesterday only, "
        f"default {default}); days are oldest first, end with yesterday, and "
        "never include today. Map the user's request to days (e.g. 'last 3 days' "
        f"-> 3). More than {_PAST_DAYS_MAX} days is not allowed: if the user asks "
        f"for more, tell them only the last {_PAST_DAYS_MAX} days are available."
    )


_VPD_STATUS = (
    "VPD (vapour pressure deficit, kPa) is how dry the air is for the plants. "
    "`status` bands: 'Danger (Too Low - Disease Risk)' below 0.4, 'Low Stress' "
    "0.4-0.8, 'Optimal' 0.8-1.2, 'High Stress' 1.2-1.6, 'Danger (Too High - "
    "Wilting Risk)' above 1.6. `source` is 'device' (the farm's own device; a "
    "greenhouse reads the air inside it) or 'model' (from the weather)."
)

_ALERT_FIELDS = (
    "Each alert has `severity` (from lowest to highest: Info, Warning, High, "
    "Critical), `category` (e.g. Heat Stress, Disease Risk, Irrigation, Wind, "
    "Spraying), `title`, `description` (why it was raised), and `action` (what "
    "the farmer should do); the *Ar fields hold the same text in Arabic, so "
    "answer in the user's language. `cropId` null means the alert is about the "
    "whole farm, not one crop. If the user asks about one crop, answer only for "
    "it, matching cropName, cropNameAr, or aliasCropName loosely. Any text field "
    "can be null. An empty `alerts` list means the farm has no alerts."
)

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
    get_current_alerts: (
        "Get the alerts of the authenticated farmer's farms for today and the "
        "next 3 days, from the weather, the crops, and the farm's devices. `date` "
        "is the day the alert is about (YYYY-MM-DD); null means today. "
        + _ALERT_FIELDS
        + "\n\n"
        + _FARM_SCOPE_RULES
    ),
    get_past_alerts: (
        "Get the past alerts of the authenticated farmer's farms, including "
        "alerts that have already ended. `day` has only two options: "
        "'yesterday' or 'before-yesterday' (the day before yesterday). Omit it to "
        "get both days together, e.g. when the user does not say which. Older "
        "days are not available: if the user asks for them, say so. `date` is "
        "always set; use it to tell the two days apart. "
        + _ALERT_FIELDS
        + "\n\n"
        + _FARM_SCOPE_RULES
    ),
    get_current_vpd: (
        "Get the VPD right now for the authenticated farmer's farms, with its "
        "status, trend, and what to do. `trend` is 'Rising Fast', 'Rising', "
        "'Stable', 'Falling', or 'Falling Fast'. `recommendation` is in English; "
        "pass it on in the user's language. `temperature` (°C) and `humidity` (%) "
        "are what VPD was calculated from; `time` is when it was read. "
        + _VPD_STATUS
        + "\n\n"
        + _FARM_SCOPE_RULES
    ),
    get_past_vpd: (
        "Get the average VPD and its status for each past day on the "
        "authenticated farmer's farms, e.g. to answer 'was yesterday a stressful "
        "day?'. " + _past_days_rules(1) + " " + _VPD_STATUS + "\n\n"
        + _FARM_SCOPE_RULES
    ),
    get_farm_report: (
        "Get the report of one of the authenticated farmer's farms for a date "
        "range: the farm's crops, and for each day the weather, the VPD, and each "
        "crop's water need, plus the alerts of those days. It is the same data as "
        "the PDF on the Nojo reports page.\n\n"
        "farm_id is required: if the user has not said which farm, ask them, then "
        "resolve its farmId with get_farms_and_crops_ids, matching the name "
        "loosely (accept typos); if nothing matches, tell the user and list their "
        "farms. If the user has not given the dates, ask them, suggesting the "
        "last 7 days.\n"
        f"Dates: reports cover only the last {_REPORT_DAYS} days including today. "
        f"from_date can be at most {_REPORT_DAYS - 1} days ago, to_date can be "
        "today at the latest, and from_date must not be after to_date. If the "
        "user asks for older days (e.g. 'last month'), do not call this tool: "
        f"tell them Nojo reports cover only the last week and offer the last "
        f"{_REPORT_DAYS} days instead.\n"
        "Report fields: days[].weather has maxTemp / minTemp (°C), humidity (%), "
        "solarRadiation (MJ/m²), and for open-field farms windSpeed (m/s) and rain "
        "(mm); days[].vpd (kPa) with vpdStatus; days[].irrigation has each crop's "
        "waterMm (mm) and waterM3 (m³), and totalWaterM3 is all crops together. "
        "`alerts` have the same fields as get_current_alerts; the *Ar fields hold "
        "Arabic text, so answer in the user's language. A null value means there "
        "is no data: say so and never guess.\n"
        "Show the report to the user as text, then give them `reportsPageUrl` and "
        "tell them: to download the report as a PDF file, open this link (they "
        "pick the farm and the dates there)."
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
    get_current_weather: (
        "Get the weather right now for the authenticated farmer's farms: "
        "temperature (°C), humidity (%), and solar radiation (W/m²); open-field "
        "farms also get wind speed (m/s) and today's rain so far (mm).\n\n"
        + _WEATHER_RULES
    ),
    get_forecasting_weather: (
        "Get the daily weather forecast for the next 7 days, today first, for the "
        "authenticated farmer's farms. Each day has date (YYYY-MM-DD), maxTemp / "
        "minTemp (°C), average humidity (%), and total solarRadiation (MJ/m²); "
        "open-field farms also get the day's highest windSpeed (m/s) and total "
        "rain (mm). Pick the right day by date for questions like 'tomorrow' or "
        "'this weekend'.\n\n" + _WEATHER_RULES
    ),
    get_past_weather: (
        "Get the daily weather of past days for the authenticated farmer's farms. "
        + _past_days_rules(_PAST_DAYS_MAX)
        + " Same fields and units per day as get_forecasting_weather.\n\n"
        + _WEATHER_RULES
    ),
    get_current_irrigation: (
        "Get today's irrigation plan for every crop on the authenticated farmer's "
        "farms: whether to irrigate, how much water, and for how long.\n"
        "Per crop: `status` is 'optimal' (irrigate the normal amount), 'increase' "
        "(soil is dry, irrigate more), 'reduce' (soil is wet enough, irrigate "
        "less), 'skip' (soil is very wet, no irrigation today), 'rest' (the tree "
        "is dormant, no irrigation), or 'not_active' (not planted yet or season "
        "ended); `waterMm` is the water depth over the crop's land (mm), `waterM3` "
        "the same water as volume for the whole land (m³), and `runtimeHours` how "
        "long to run the irrigation system (can be null, e.g. in a greenhouse); "
        "`growthStage` is initial, development, mid, late, or post-harvest. If the "
        "user asks about one crop, answer only for it, matching cropName, "
        "cropNameAr, or aliasCropName loosely.\n\n" + _FARM_SCOPE_RULES
    ),
    get_past_irrigation: (
        "Get how much water each crop on the authenticated farmer's farms needed "
        "on each past day: `waterMm` (mm depth over the crop's land) and `waterM3` "
        "(m³ for the whole land). There is no status for past days, so never say "
        "a past day was a skip or increase day. "
        + _past_days_rules(_PAST_DAYS_MAX)
        + " If the user asks about one crop, answer only for it, matching "
        "cropName, cropNameAr, or aliasCropName loosely.\n\n" + _FARM_SCOPE_RULES
    ),
    get_ledger: (
        "Get the authenticated farmer's ledger: every money entry they recorded "
        "in Nojo (what they spent or earned, on what, for which crop, and when), "
        "newest first, with each farm's `totalAmount`.\n"
        "Each entry has `entryId` (needed to edit or delete it), `date`, `action` "
        "(e.g. Expense, Payment, Purchase, Harvest), `category` (what it was for, "
        "e.g. Fertilizer, Seeds, Labor, Water, Fuel), `amount`, the crop names, "
        "`description` and `notes`. Amounts are in the farm's `currency` (e.g. "
        "EGP, SAR); always show the currency with them. `cropId` null means the "
        "entry is for the whole farm, not one crop. The *Ar fields hold the same "
        "text in Arabic, so answer in the user's language. Any text field can be "
        "null. An empty `entries` list means the farm has no ledger entries yet. "
        "If the user asks about one crop, answer only for it, matching cropName, "
        "cropNameAr, or aliasCropName loosely.\n\n" + _FARM_SCOPE_RULES
    ),
    get_ledger_options: (
        "List the actions and categories a ledger entry can use, as names and ids "
        "only, the same choices as the website's add-entry form.\n\n"
        'Returns {"actions": [{"actionId": str, "name": str, "nameAr": str}], '
        '"categories": [{"categoryId": str, "name": str, "nameAr": str}]}.\n'
        "Call this when adding or editing a ledger entry to turn the user's action "
        "(what kind of entry, e.g. Purchase) and category (what it was for, e.g. "
        "Fertilizer) into ids. Match the user's words loosely against both name "
        "and nameAr, accepting typos. If nothing fits, use the one named 'Other' "
        "and keep the user's own words for it. Never invent an id."
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


_SEND_FEEDBACK_DESCRIPTION = (
    "Send the user's feedback to the Nojo team, who receive it by email: a "
    "problem they found, a suggestion, or anything else they want to tell "
    "Nojo.\n\n"
    "Write `message` as a clear note in the user's own words and language, "
    "keeping their details (which page, farm, or crop). It must be "
    f"{_FEEDBACK_MIN}-{_FEEDBACK_MAX} characters. Never include passwords or "
    "other secrets. Before calling, show the user the exact text and ask them to "
    "confirm; call only after they agree. After it is sent, tell the user the "
    "Nojo team received it.\n"
    'Returns {"sent": true, "feedback_id": str, "created_at": str}.'
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


_LEDGER_INPUT_RULES = (
    "- action_id and category_id: the actionId and categoryId from "
    "get_ledger_options. If the chosen action is 'Other', pass the user's own "
    "name for it as `description`; if the chosen category is 'Other', pass "
    f"theirs as `description_ar`. Each at most {_LEDGER_TEXT_MAX} characters.\n"
    "- amount: the money as a number, more than 0 and at most 9,999,999,999, in "
    "the farm's currency (see get_ledger). Never convert it.\n"
    "- entry_date: when it happened, ISO date and time, not in the future. Omit "
    "it for now.\n"
    "A harvest can't be recorded as an entry: on the website it is recorded by "
    "ending the crop's cycle. If the user wants that, send them to the ledger page "
    "on the Nojo website.\n"
    "Entries can't be added, edited, or deleted once the crop's cycle or the "
    "farm's cycle has ended (harvested). If Nojo says so, tell the user and do "
    "not retry.\n"
)

_ADD_LEDGER_ENTRY_DESCRIPTION = (
    "Add a new money entry (an expense, payment, purchase, ...) to one of the "
    "authenticated farmer's farms' ledger.\n\n"
    "Resolve the ids first; never invent one:\n"
    "- farm_id and crop_id: a farmId and one of its cropIds from "
    "get_farms_and_crops_ids, matching the names the user gave loosely (accept "
    "typos). The crop is required and must be on that farm; if the user did not "
    "say which crop, ask them.\n"
    + _LEDGER_INPUT_RULES
    + "Before calling, show the user the entry (farm, crop, action, category, "
    "amount with currency, date) and ask them to confirm; call only after they "
    "agree.\n"
    "Returns the saved entry, including its id. `amount` comes back as text; read "
    "it as a number."
)

_EDIT_LEDGER_ENTRY_DESCRIPTION = (
    "Change one or more details of an existing entry in the authenticated "
    "farmer's ledger: its crop, action, category, amount, or date.\n\n"
    "`entry_id` must be an entryId returned by get_ledger: find the entry the "
    "user means there (by date, amount, category, or crop); if several could "
    "match, ask the user which one. A new crop_id must be a cropId on the same "
    "farm from get_farms_and_crops_ids.\n"
    "Pass only the fields the user wants to change and do not ask about the "
    "others:\n"
    + _LEDGER_INPUT_RULES
    + "Before calling, show the user the change and ask them to confirm; call "
    "only after they agree.\n"
    "Returns the updated entry. `amount` comes back as text; read it as a number."
)

_DELETE_LEDGER_ENTRY_DESCRIPTION = (
    "Permanently delete one entry from the authenticated farmer's ledger.\n\n"
    "`entry_id` must be an entryId returned by get_ledger: find the entry the "
    "user means there (by date, amount, category, or crop); if several could "
    "match, ask the user which one. Before calling, always ask the user to "
    "confirm, naming the entry (e.g. 'Delete the 1,250.5 EGP Fertilizer purchase "
    "of 22 Sep on North Farm?'), and call only after they agree. An entry can't "
    "be deleted once its crop's or farm's cycle has ended; if Nojo says so, tell "
    "the user and do not retry.\n"
    'Returns {"deleted": true, "entry_id": str, "message": str}.'
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
    mcp.tool(annotations=_CREATE, description=_SEND_FEEDBACK_DESCRIPTION)(
        send_feedback
    )
    mcp.tool(annotations=_IDEMPOTENT_WRITE, description=_EDIT_CROP_DESCRIPTION)(
        edit_crop
    )
    mcp.tool(annotations=_CREATE, description=_ADD_LEDGER_ENTRY_DESCRIPTION)(
        add_ledger_entry
    )
    mcp.tool(
        annotations=_IDEMPOTENT_WRITE, description=_EDIT_LEDGER_ENTRY_DESCRIPTION
    )(edit_ledger_entry)
    mcp.tool(annotations=_DESTRUCTIVE, description=_DELETE_LEDGER_ENTRY_DESCRIPTION)(
        delete_ledger_entry
    )
