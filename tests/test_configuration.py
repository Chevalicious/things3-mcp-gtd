"""Unit tests for configuration loading and validation.

Tests that settings are correctly loaded and validated.
"""

import pytest
from pydantic import ValidationError

from things_mcp.settings import get_settings, Settings


@pytest.mark.unit
class TestConfiguration:
    """Test configuration management."""

    def test_default_settings(self):
        """Default settings should be valid."""
        settings = get_settings()
        assert settings.things_mcp_host == "127.0.0.1"
        assert settings.things_mcp_port == 8009
        assert settings.things_mcp_transport == "streamable-http"

    def test_transport_mode_validation(self):
        """Support stdio and Streamable HTTP."""
        # Valid mode
        settings = Settings(things_mcp_transport="streamable-http")
        assert settings.things_mcp_transport == "streamable-http"

        assert Settings(things_mcp_transport="stdio").things_mcp_transport == "stdio"

        # Invalid modes should raise ValidationError
        with pytest.raises(ValidationError):
            Settings(things_mcp_transport="both")

        with pytest.raises(ValidationError):
            Settings(things_mcp_transport="sse")

        with pytest.raises(ValidationError):
            Settings(things_mcp_transport="invalid")

    def test_port_validation(self):
        """Port should be validated within valid range."""
        # Valid ports should work
        settings = Settings(things_mcp_port=8009)
        assert settings.things_mcp_port == 8009

        settings = Settings(things_mcp_port=1)
        assert settings.things_mcp_port == 1

        settings = Settings(things_mcp_port=65535)
        assert settings.things_mcp_port == 65535

        # Invalid ports should raise ValidationError
        with pytest.raises(ValidationError):
            Settings(things_mcp_port=70000)  # Too high

        with pytest.raises(ValidationError):
            Settings(things_mcp_port=0)  # Too low

    def test_host_validation(self):
        """Host should accept valid IP addresses."""
        valid_hosts = ["127.0.0.1", "0.0.0.0", "localhost", "192.168.1.1"]
        for host in valid_hosts:
            settings = Settings(things_mcp_host=host)
            assert settings.things_mcp_host == host

    def test_auth_token_property(self):
        """has_auth_token property should work correctly."""
        settings = Settings(things_auth_token="test-token")
        assert settings.has_auth_token is True

        settings = Settings(things_auth_token="")
        assert settings.has_auth_token is False
