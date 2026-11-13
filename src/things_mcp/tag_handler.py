"""Resolve tags without invoking AppleScript unless the owner opts in."""

import things
from fastmcp.exceptions import ToolError

from .applescript_bridge import escape_applescript_string, run_applescript
from .settings import get_settings


def existing_tag_names() -> dict[str, str]:
    return {tag["title"].casefold(): tag["title"] for tag in things.tags()}


def missing_tags(tags: list[str], existing: dict[str, str]) -> list[str]:
    if any(not isinstance(tag, str) or not tag.strip() or "," in tag for tag in tags):
        raise ToolError("Tag names must be nonempty and cannot contain commas.")
    return [tag for tag in dict.fromkeys(tags) if tag.casefold() not in existing]


def prepare_tags(tags: list[str]) -> None:
    """Check requested tags before dispatch, or create missing tags by opt-in."""
    if not tags:
        return
    missing = missing_tags(tags, existing_tag_names())
    if not missing:
        return
    if not get_settings().things_mcp_allow_tag_creation:
        raise ToolError(
            "Unknown Things tag(s): "
            + ", ".join(missing)
            + ". Create them in Things under Window → Tags, then retry."
        )

    script = ['tell application id "com.culturedcode.ThingsMac"']
    for tag in missing:
        escaped = escape_applescript_string(tag)
        script.extend(
            [
                f'  set tagName to "{escaped}"',
                "  if not (exists (first tag whose name is tagName)) then",
                "    make new tag with properties {name:tagName}",
                "  end if",
            ]
        )
    script.append("end tell")

    if run_applescript("\n".join(script)) is False:
        raise ToolError(
            "Could not create Things tags. Create them in Things or check macOS Automation permission."
        )
