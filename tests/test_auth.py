import base64
import time

import httpx
import pytest
from tests.conftest import TOKEN_EXCHANGE_URL, make_settings

from src.services.auth import ExchangeTokenVerifier, exchange_token
from src.services.errors import NojoAPIError, TokenExchangeRejectedError

GOOD_BODY = {
    "access_token": "nojo-jwt-user-1",
    "expires_in": 900,
    "sub": "user-1",
    "client_id": "https://claude.ai/oauth/mcp-oauth-client-metadata",
}


def client_returning(response: httpx.Response | Exception) -> httpx.AsyncClient:
    def handler(_: httpx.Request) -> httpx.Response:
        if isinstance(response, Exception):
            raise response
        return response

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_successful_exchange_is_parsed():
    settings = make_settings()
    async with client_returning(httpx.Response(200, json=GOOD_BODY)) as http:
        result = await exchange_token(http, settings, "oauth-token")

    assert result.nojo_jwt == "nojo-jwt-user-1"
    assert result.subject == "user-1"
    assert result.expires_in == 900


async def test_client_id_falls_back_when_the_backend_omits_it():
    settings = make_settings()
    body = {k: v for k, v in GOOD_BODY.items() if k != "client_id"}
    async with client_returning(httpx.Response(200, json=body)) as http:
        result = await exchange_token(http, settings, "oauth-token")

    assert result.client_id is None


@pytest.mark.parametrize(
    "body",
    [
        {"error": "invalid_grant"},
        {"error": "something_else"},
        {},
        "not json at all",
    ],
)
async def test_a_400_rejects_the_subject_token(body):
    """Any 400 that is not invalid_request means the caller must sign in again."""
    settings = make_settings()
    kwargs = {"json": body} if isinstance(body, dict) else {"text": body}
    async with client_returning(httpx.Response(400, **kwargs)) as http:
        with pytest.raises(TokenExchangeRejectedError):
            await exchange_token(http, settings, "oauth-token")


async def test_a_400_invalid_request_is_our_bug_not_a_rejected_token():
    """Returning 401 here would send the client through sign-in forever."""
    settings = make_settings()
    async with client_returning(
        httpx.Response(400, json={"error": "invalid_request"})
    ) as http:
        with pytest.raises(NojoAPIError) as excinfo:
            await exchange_token(http, settings, "oauth-token")

    assert not isinstance(excinfo.value, TokenExchangeRejectedError)


async def test_a_401_is_this_server_being_rejected_not_the_caller():
    """401 invalid_client means our own credentials are wrong: a config problem."""
    settings = make_settings()
    async with client_returning(
        httpx.Response(401, json={"error": "invalid_client"})
    ) as http:
        with pytest.raises(NojoAPIError) as excinfo:
            await exchange_token(http, settings, "oauth-token")

    assert not isinstance(excinfo.value, TokenExchangeRejectedError)


async def test_rate_limiting_is_not_a_rejected_token():
    settings = make_settings()
    async with client_returning(
        httpx.Response(429, json={"error": "temporarily_unavailable"})
    ) as http:
        with pytest.raises(NojoAPIError) as excinfo:
            await exchange_token(http, settings, "oauth-token")

    assert not isinstance(excinfo.value, TokenExchangeRejectedError)


@pytest.mark.parametrize("status_code", [403, 500, 503])
async def test_other_statuses_raise_a_backend_error(status_code):
    settings = make_settings()
    async with client_returning(httpx.Response(status_code, text="nope")) as http:
        with pytest.raises(NojoAPIError) as excinfo:
            await exchange_token(http, settings, "oauth-token")

    assert not isinstance(excinfo.value, TokenExchangeRejectedError)
    assert str(status_code) in str(excinfo.value)


@pytest.mark.parametrize(
    "body",
    [
        {"expires_in": 900, "sub": "user-1"},
        {"access_token": "", "expires_in": 900, "sub": "user-1"},
        {"access_token": "jwt", "expires_in": 900},
        {"access_token": "jwt", "expires_in": "soon", "sub": "user-1"},
    ],
)
async def test_a_malformed_body_is_a_backend_error(body):
    settings = make_settings()
    async with client_returning(httpx.Response(200, json=body)) as http:
        with pytest.raises(NojoAPIError):
            await exchange_token(http, settings, "oauth-token")


async def test_a_transport_failure_is_a_backend_error():
    settings = make_settings()
    async with client_returning(httpx.ConnectError("down")) as http:
        with pytest.raises(NojoAPIError):
            await exchange_token(http, settings, "oauth-token")


async def test_the_error_message_never_quotes_the_backend_body():
    settings = make_settings()
    secret_body = "eyJhbGciOi.super-secret-jwt.signature"
    async with client_returning(httpx.Response(502, text=secret_body)) as http:
        with pytest.raises(NojoAPIError) as excinfo:
            await exchange_token(http, settings, "oauth-token")

    assert "super-secret-jwt" not in str(excinfo.value)


async def test_the_verifier_caches_a_verified_token():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=GOOD_BODY)

    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    first = await verifier.verify_token("oauth-token")
    second = await verifier.verify_token("  oauth-token  ")

    assert first is second
    assert len(calls) == 1
    assert first.nojo_jwt == "nojo-jwt-user-1"


async def test_forget_evicts_the_cache_entry():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=GOOD_BODY)

    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    await verifier.verify_token("oauth-token")
    verifier.forget("oauth-token")
    await verifier.verify_token("oauth-token")

    assert len(calls) == 2


async def test_an_expired_entry_is_exchanged_again():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={**GOOD_BODY, "expires_in": 1})

    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    await verifier.verify_token("oauth-token")
    # expires_in is below the 60s safety margin, so the entry is already stale.
    await verifier.verify_token("oauth-token")

    assert len(calls) == 2


async def test_a_rejected_token_verifies_as_none():
    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = client_returning(
        httpx.Response(400, json={"error": "invalid_grant"})
    )

    assert await verifier.verify_token("oauth-token") is None


async def test_a_backend_outage_propagates_rather_than_reading_as_invalid():
    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = client_returning(httpx.Response(503, text="down"))

    with pytest.raises(NojoAPIError):
        await verifier.verify_token("oauth-token")


async def test_an_empty_token_is_rejected_without_a_backend_call():
    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = client_returning(httpx.Response(200, json=GOOD_BODY))

    assert await verifier.verify_token("   ") is None


async def test_no_http_client_verifies_as_none():
    verifier = ExchangeTokenVerifier(make_settings())

    assert await verifier.verify_token("oauth-token") is None


async def test_credentials_are_urlencoded_before_base64():
    """RFC 6749 2.3.1, and what the backend documents it decodes."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=GOOD_BODY)

    settings = make_settings(
        MCP_OAUTH_CLIENT_ID="nojo mcp", MCP_OAUTH_CLIENT_SECRET="p:a+s/s word"
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        await exchange_token(http, settings, "oauth-token")

    expected = base64.b64encode(b"nojo%20mcp:p%3Aa%2Bs%2Fs%20word").decode()
    assert seen[0].headers["authorization"] == f"Basic {expected}"


async def test_the_exchange_posts_to_the_configured_url():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=GOOD_BODY)

    settings = make_settings()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        await exchange_token(http, settings, "oauth-token")

    assert str(seen[0].url) == TOKEN_EXCHANGE_URL
    assert seen[0].method == "POST"


async def test_the_access_token_carries_the_issuer_claim():
    verifier = ExchangeTokenVerifier(make_settings())
    verifier.http_client = client_returning(httpx.Response(200, json=GOOD_BODY))

    token = await verifier.verify_token("oauth-token")

    assert token.claims["iss"] == make_settings().issuer_url
    assert token.scopes == []
    assert token.expires_at > time.time()
