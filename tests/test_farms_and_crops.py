import httpx
import pytest

from src.helpers.farms_and_crops import get_farms_and_crops_ids
from src.services.errors import NojoAPIRequestError
from src.services.nojo_client import NojoClient
from tests.conftest import make_settings

OVERVIEW = [
    {
        "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "farmName": "North Field",
        "crops": [
            {
                "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
                "cropName": "Avocado",
                "cropNameAr": "أفوكادو",
            }
        ],
    }
]


SETTINGS = make_settings()


def _client(status: int, body: object, requests: list[httpx.Request]) -> NojoClient:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json=body)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return NojoClient(http_client, SETTINGS)


async def test_returns_farms_and_crops_from_the_overview_endpoint():
    requests: list[httpx.Request] = []
    farms = await get_farms_and_crops_ids(
        _client(200, OVERVIEW, requests), SETTINGS, "jwt-1"
    )

    assert farms == OVERVIEW
    assert requests[0].url.path == "/api/farms/overview"
    assert requests[0].headers["authorization"] == "Bearer jwt-1"


@pytest.mark.parametrize("status, body", [(200, {"not": "a list"}), (500, {"error": "boom"})])
async def test_bad_responses_raise(status, body):
    with pytest.raises(NojoAPIRequestError):
        await get_farms_and_crops_ids(_client(status, body, []), SETTINGS, "jwt-1")
