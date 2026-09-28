import httpx
import pytest

from src.helpers.crop_options import get_crop_options
from src.services.errors import NojoAPIRequestError
from src.services.nojo_client import NojoClient
from tests.conftest import make_settings

OPTIONS = {
    "cropTypes": [{"cropId": "c-1", "cropName": "Wheat", "cropNameAr": "قمح"}],
    "soilTypes": [{"soilId": "s-1", "soilName": "Clay"}],
    "irrigationSystems": [{"irrigationId": "i-1", "irrigationName": "Drip"}],
}
SETTINGS = make_settings()


def _client(status: int, body: object, requests: list[httpx.Request]) -> NojoClient:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json=body)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return NojoClient(http_client, SETTINGS)


async def test_returns_the_options_from_the_options_endpoint():
    requests: list[httpx.Request] = []
    options = await get_crop_options(_client(200, OPTIONS, requests), SETTINGS, "jwt-1")

    assert options == OPTIONS
    assert requests[0].url.path == "/api/crops/options"
    assert requests[0].headers["authorization"] == "Bearer jwt-1"


@pytest.mark.parametrize(
    "status, body",
    [
        (200, [OPTIONS]),
        (200, {"cropTypes": [], "soilTypes": []}),
        (200, {**OPTIONS, "irrigationSystems": None}),
        (500, {"error": "boom"}),
    ],
)
async def test_bad_responses_raise(status, body):
    with pytest.raises(NojoAPIRequestError):
        await get_crop_options(_client(status, body, []), SETTINGS, "jwt-1")
