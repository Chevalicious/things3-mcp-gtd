"""Legacy configuration shim for ``scripts/configure_token.py``.

The application's primary configuration mechanism is :mod:`pydantic-settings`
in :mod:`things_mcp.settings` (env vars + ``.env``). This module exists only
to read and write ``~/.things-mcp/config.json`` so that the interactive
``configure_token.py`` helper has a place to stash the auth token without
requiring users to edit a dotfile by hand.

Lookup priority for the auth token:

1. Environment variable / ``.env`` (via :mod:`pydantic-settings`)
2. ``~/.things-mcp/config.json`` (this file)
"""

import json
import logging
from pathlib import Path

from .settings import get_settings

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".things-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load_legacy_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load legacy config file: {e}")
        return {}


def _save_legacy_config(config: dict) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save config file: {e}")
        return False


def get_things_auth_token() -> str:
    """Return the Things authentication token, or an empty string if unset."""
    settings = get_settings()
    if settings.has_auth_token:
        logger.debug("Using Things auth token from environment/.env")
        return settings.things_auth_token

    token = _load_legacy_config().get("things_auth_token", "")
    if token:
        logger.debug("Using Things auth token from %s", CONFIG_FILE)
        return token

    logger.warning(
        "No Things auth token found. Set THINGS_AUTH_TOKEN in .env or run "
        "scripts/configure_token.py."
    )
    return ""


def set_things_auth_token(token: str) -> bool:
    """Persist the Things authentication token to ``~/.things-mcp/config.json``."""
    legacy_config = _load_legacy_config()
    legacy_config["things_auth_token"] = token
    return _save_legacy_config(legacy_config)
