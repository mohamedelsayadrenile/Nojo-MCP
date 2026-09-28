import logging
from typing import Any

from src.core.config import Settings
from src.services.errors import NojoAPIRequestError
from src.services.nojo_client import NojoClient

logger = logging.getLogger(__name__)

_LISTS = ("cropTypes", "soilTypes", "irrigationSystems")


async def get_crop_options(
    nojo_client: NojoClient, settings: Settings, jwt: str
) -> dict[str, Any]:
    """Return the crop types, soil types, and irrigation systems a crop can use.

    Shape: {"cropTypes": [{"cropId", "cropName", "cropNameAr"}],
            "soilTypes": [{"soilId", "soilName"}],
            "irrigationSystems": [{"irrigationId", "irrigationName"}]}.
    """
    path = settings.crop_options_path
    options = await nojo_client.get(jwt, path)
    if not isinstance(options, dict) or not all(
        isinstance(options.get(key), list) for key in _LISTS
    ):
        logger.warning("crop_options_failed path=%s reason=malformed_response", path)
        raise NojoAPIRequestError(
            f"The Nojo platform API returned an unexpected response for {path}."
        )
    return options
