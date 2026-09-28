import logging
from typing import Any

from src.core.config import Settings
from src.services.errors import NojoAPIRequestError
from src.services.nojo_client import NojoClient

logger = logging.getLogger(__name__)


async def get_farms_and_crops_ids(
    nojo_client: NojoClient, settings: Settings, jwt: str
) -> list[dict[str, Any]]:
    """Return the user's farms and their crops, as ids and names only.

    Shape: [{"farmId", "farmName", "crops": [{"cropId", "cropName", "cropNameAr"}]}].
    Internal helper for tools that need a farm or crop id; not exposed as an MCP tool.
    """
    path = settings.farms_overview_path
    farms = await nojo_client.get(jwt, path)
    if not isinstance(farms, list):
        logger.warning("farms_overview_failed path=%s reason=malformed_response", path)
        raise NojoAPIRequestError(
            f"The Nojo platform API returned an unexpected response for {path}."
        )
    return farms
