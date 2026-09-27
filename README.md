# Nojo-MCP

A remote [MCP](https://modelcontextprotocol.io) server for the Nojo platform, served over
Streamable HTTP at `https://nojo.ai/mcp`.

It is currently an **OAuth bridge only**. The sign-in chain is the thing being proved; platform
tools come later, on top of it.

## Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `whoami` | none | `{"subject", "client_id", "token_expires_at", "exchange": "ok"}` |

`whoami` makes no upstream call. It reports what the token exchange already established, so a
successful call is a green light for the whole chain: discovery → authorize → token → exchange.

## How authentication works

This server is an OAuth **resource server**, never an authorization server. It issues no tokens
and stores no passwords.

1. A client (Claude, ChatGPT, Codex) hits `/mcp` with no token and gets `401` plus a
   `WWW-Authenticate` header naming `/.well-known/oauth-protected-resource/mcp`.
2. That document points the client at the Nojo backend as the authorization server. The client
   does login, consent and PKCE there and comes back with an OAuth access token.
3. On each request this server exchanges that token at the backend
   ([RFC 8693](https://www.rfc-editor.org/rfc/rfc8693)), authenticating with its own client
   credentials, and gets a short-lived Nojo JWT plus the user's `sub`.
4. The exchange result is cached until 60s before expiry.

The Nojo JWT never leaves the server — it is excluded from the token's repr and serialization, so
it cannot reach the model or the client.

Failure modes are kept distinct on purpose. Only a dead user token earns a `401`:

- Backend rejects the user's token (`400 invalid_grant`) → `401` back to the client, which
  re-authenticates.
- Backend rejects **this server** (`401 invalid_client`, `400 invalid_request`) → `500`, logged at
  `ERROR`. These mean our credentials or our request are wrong, so signing in again cannot help; a
  `401` here would put the client in an endless sign-in loop. Check `MCP_OAUTH_CLIENT_ID` and
  `MCP_OAUTH_CLIENT_SECRET`, and that the backend has registered this client.
- Backend is down, rate limiting, or broken (`429`, `5xx`, unreachable, malformed body) → `500`. A
  client must not read an outage as "your login expired" and loop through sign-in.

`/.well-known/oauth-authorization-server` and `/oauth/*` are deliberately **not** served here —
they belong to the backend. See `MCP_APIs_Contract.md` for the endpoints the backend must provide.

### Proxy routing (required)

The authorization server and this server share the host `nojo.ai`, so the reverse proxy must split
them:

| Path on `nojo.ai` | Served by |
| --- | --- |
| `/.well-known/oauth-authorization-server` | Backend |
| `/oauth/authorize`, `/oauth/token` | Backend |
| `/.well-known/oauth-protected-resource/mcp` | **This server** |
| `/mcp` | **This server** |

If a backend catch-all swallows `/.well-known/oauth-protected-resource/mcp`, discovery fails with
no visible error. Check this first when a connector will not connect.

## Setup

```bash
uv sync
cp src/.env.example src/.env   # then fill in MCP_OAUTH_CLIENT_SECRET
chmod 600 src/.env
uv run uvicorn src.app:app --port 8000
```

Settings are read once at import and cached, so any `src/.env` edit needs a process restart. A
missing required value surfaces as a pydantic `ValidationError` while uvicorn is importing
`src.app`, before the server binds.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `NOJO_ISSUER_URL` | yes | — | Authorization server issuer, exact string, no trailing slash |
| `NOJO_RESOURCE_SERVER_URL` | yes | — | Public URL of this server including `/mcp`; drives the 401 challenge and the metadata route |
| `TOKEN_EXCHANGE_URL` | yes | — | Backend RFC 8693 endpoint |
| `MCP_OAUTH_CLIENT_ID` | yes | — | This server's confidential client id |
| `MCP_OAUTH_CLIENT_SECRET` | yes | — | Its secret; keep out of version control |
| `HOST` | no | `0.0.0.0` | Bind address |
| `ALLOWED_HOSTS` | no | empty | Host allowlist; a request for an unlisted host gets `421` |
| `ALLOWED_ORIGINS` | no | empty | Origin allowlist |
| `STATELESS_HTTP` | no | `false` | Set true only for multiple replicas without sticky routing |
| `HTTP_TIMEOUT_SECONDS` | no | `15.0` | Token-exchange timeout |
| `HTTP_MAX_CONNECTIONS` | no | `100` | Shared connection pool size |
| `LOG_LEVEL` | no | `INFO` | |

`ALLOWED_HOSTS` accepts a bare hostname and matches it on any port.

## Deployment

```bash
docker build -t nojo-mcp .
docker run -p 8000:8000 --env-file src/.env nojo-mcp
```

Runs as a non-root user with a `/healthz` healthcheck. Terminate TLS at the proxy and pass
`--proxy-headers` (already in the image's `CMD`); set `FORWARDED_ALLOW_IPS` to the proxy's network
so the app sees the real scheme and host. `NOJO_RESOURCE_SERVER_URL` must be the public HTTPS URL,
not the internal one — clients compare it exactly.

## Staging

Nothing about the host is baked into the code — `NOJO_ISSUER_URL`, `NOJO_RESOURCE_SERVER_URL`,
`TOKEN_EXCHANGE_URL` and `ALLOWED_HOSTS` are the whole story, so the same build points at staging or
production by env alone. `src/.env.example` currently carries the staging host
`41.38.196.107.nip.io`; production is `nojo.ai`.

All four must move together, and the backend has to agree:

- Its `/.well-known/oauth-authorization-server` must advertise `issuer` as the **same string** as
  `NOJO_ISSUER_URL`. RFC 8414 compares issuers byte for byte.
- Its configured resource identifier must equal `NOJO_RESOURCE_SERVER_URL` exactly, because API 2
  binds the token's audience to it.
- The reverse proxy on that host must forward `/mcp` and
  `/.well-known/oauth-protected-resource/mcp` here (see the routing table above).
- The host needs a certificate clients will accept. Claude and ChatGPT both refuse a self-signed
  cert, and the resulting connector error does not say so.

## Connecting a client

Add `https://nojo.ai/mcp` (or the staging URL) as a custom connector. The client discovers the
authorization server on its own, walks the sign-in flow, and then `whoami` should return the
signed-in user's id.

From the Claude Code CLI:

```bash
claude mcp add --transport http nojo https://41.38.196.107.nip.io/mcp
```

Then run `/mcp` in a session to authenticate.

## Development

```bash
uv run pytest
```

Tests use `httpx.MockTransport` for the backend and an ASGI transport for the server, so nothing
touches the network.

```
src/
  app.py              ASGI app; Streamable HTTP at /mcp
  server.py           MCP server, lifespan, /healthz
  tools.py            AppState and the whoami tool
  core/config.py      Settings
  core/logging.py     Logging setup
  services/auth.py    Token exchange and the verifier cache
  services/http.py    Shared httpx client
  services/errors.py  Error types
```
