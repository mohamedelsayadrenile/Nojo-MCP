from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _split_csv(value: object) -> object:
    """Parse a comma-separated list and add a `:*` variant so bare hosts match any port."""
    if isinstance(value, str):
        value = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list):
        return value

    expanded: list[str] = []
    for item in value:
        expanded.append(item)
        if not item.endswith(":*"):
            expanded.append(f"{item}:*")
    return expanded


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    issuer_url: str = Field(alias="NOJO_ISSUER_URL")
    resource_server_url: str = Field(alias="NOJO_RESOURCE_SERVER_URL")
    nojo_api_base_url: str = Field(alias="NOJO_API_BASE_URL")
    farms_overview_path: str = Field(alias="NOJO_FARMS_OVERVIEW_PATH", min_length=1)
    farms_path: str = Field(alias="NOJO_FARMS_PATH", min_length=1)
    farm_path: str = Field(alias="NOJO_FARM_PATH", pattern=r"\{farm_id\}")
    crop_path: str = Field(alias="NOJO_CROP_PATH", pattern=r"\{crop_id\}")

    token_exchange_url: str = Field(alias="TOKEN_EXCHANGE_URL")
    mcp_oauth_client_id: str = Field(alias="MCP_OAUTH_CLIENT_ID")
    mcp_oauth_client_secret: SecretStr = Field(alias="MCP_OAUTH_CLIENT_SECRET")

    host: str = Field("0.0.0.0", alias="HOST")
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=list, alias="ALLOWED_HOSTS"
    )
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=list, alias="ALLOWED_ORIGINS"
    )
    stateless_http: bool = Field(False, alias="STATELESS_HTTP")

    http_timeout_seconds: float = Field(15.0, alias="HTTP_TIMEOUT_SECONDS", gt=0)
    http_max_connections: int = Field(100, alias="HTTP_MAX_CONNECTIONS", gt=0)
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    _split_lists = field_validator("allowed_hosts", "allowed_origins", mode="before")(
        _split_csv
    )

    @field_validator("issuer_url", "resource_server_url", "nojo_api_base_url")
    @classmethod
    def remove_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator(
        "token_exchange_url", "mcp_oauth_client_id", "mcp_oauth_client_secret"
    )
    @classmethod
    def require_non_empty(cls, value: str | SecretStr) -> str | SecretStr:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not raw:
            raise ValueError("must not be empty")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
