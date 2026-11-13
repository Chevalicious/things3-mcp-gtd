"""Read the Things URL token, with a fallback for older installations."""

import json
import logging
from pathlib import Path

from .settings import get_settings

logger = logging.getLogger(__name__)
CONFIG_FILE = Path.home() / ".things-mcp" / "config.json"


def get_things_auth_token() -> str:
    """Prefer the launcher environment or .env over the legacy file."""
    if token := get_settings().things_auth_token:
        return token
    try:
        data = json.loads(CONFIG_FILE.read_text())
        token = data.get("things_auth_token") if isinstance(data, dict) else None
        return token if isinstance(token, str) else ""
    except FileNotFoundError:
        return ""
    except (ValueError, OSError):
        logger.warning("Could not read the legacy Things MCP configuration.")
        return ""
