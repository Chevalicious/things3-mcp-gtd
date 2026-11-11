"""
Settings management using pydantic-settings.

Provides type-safe, validated configuration with automatic .env file loading.
Settings are loaded once and cached for the lifetime of the application.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and .env support.

    Settings are loaded from (in order of priority):
    1. Environment variables
    2. .env file in the server's working directory
    3. Default values defined here

    Environment variables use the same names as the fields (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Server configuration
    things_mcp_host: str = Field(
        default="127.0.0.1",
        description="Host address for the MCP server to bind to",
    )
    things_mcp_port: int = Field(
        default=8009,
        ge=1,
        le=65535,
        description="Port for the MCP server to listen on",
    )
    things_mcp_transport: Literal["stdio", "streamable-http", "oauth-http"] = Field(
        default="streamable-http",
        description="Transport protocol: 'stdio' or 'streamable-http'",
    )

    # Things authentication
    things_auth_token: str = Field(
        default="",
        description="Things 3 authentication token (from Things > Settings > General > Enable Things URLs)",
    )

    things_mcp_http_token: SecretStr = SecretStr("")
    things_mcp_read_only: bool = False
    things_mcp_allow_tag_creation: bool = False
    things_mcp_allow_automation_writes: bool = False

    # OAuth runs on a separate, explicitly selected HTTP transport.
    things_mcp_oauth_url: str = ""
    things_mcp_oauth_github_client_id: str = ""
    things_mcp_oauth_github_client_secret: SecretStr = SecretStr("")
    things_mcp_oauth_github_user_id: int | None = None
    things_mcp_oauth_redirect_uris: str = ""
    things_mcp_oauth_allow_writes: bool = False

    # HTTP bearer authentication
    things_mcp_require_auth: bool = Field(
        default=False,
        description="Require a separate HTTP bearer token",
    )

    # Debug settings
    things_mcp_debug: bool = Field(
        default=False,
        description="Enable verbose debug logging to console (default: INFO only)",
    )

    @property
    def has_auth_token(self) -> bool:
        """Check if an authentication token is configured."""
        return bool(self.things_auth_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the application settings (cached singleton).

    Returns:
        Settings: The validated application settings.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    return Settings()
