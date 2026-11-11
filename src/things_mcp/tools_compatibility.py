"""Private-branch tools that use the local Things write paths."""

import asyncio
from threading import Lock

import things
from fastmcp.exceptions import ToolError

from .applescript_bridge import escape_applescript_string, run_applescript
from .cache import invalidate_caches_for
from .config import get_things_auth_token
from .settings import get_settings
from .tag_handler import prepare_tags
from .tool_annotations import TOOL_ANNOTATIONS
from .url_scheme import execute_url, update_todo
from .utils import _normalize_id
from .write_confirmation import observe

AUTOMATION_TOOLS = {"trash-task", "create-area"}
_area_lock = Lock()


def _find_task(task_id, title, *, exact=False):
    task_id = _normalize_id(task_id)
    if not task_id and title and title.strip():
        needle = title.strip().casefold()
        matches = [
            task
            for task in things.todos(status="incomplete")
            if (
                task["title"].casefold() == needle
                if exact
                else needle in task["title"].casefold()
            )
        ]
        if len(matches) != 1:
            raise ToolError("Title is missing or ambiguous. Use an exact task ID.")
        task_id = matches[0]["uuid"]
    task = things.get(task_id) if task_id else None
    if not task or task.get("type") != "to-do" or task.get("trashed"):
        raise ToolError("Provide the ID of a Things to-do outside Trash.")
    return task


def register_compatibility_tools(mcp):
    @mcp.tool(
        name="cancel-task", annotations=TOOL_ANNOTATIONS["cancel-task"], timeout=15
    )
    async def cancel_task(
        task_id: str | None = None,
        task_title: str | None = None,
        reason: str | None = None,
    ) -> str:
        """Mark a to-do canceled by ID or unambiguous title, optionally appending a reason."""

        def cancel():
            task = _find_task(task_id, task_title)
            item_id = task["uuid"]
            if task.get("status") == "canceled":
                return f"Task is already canceled. ID: `{item_id}`"
            if task.get("status") != "incomplete":
                raise ToolError("Only an incomplete task can be canceled.")
            note = f"[Canceled] {reason}" if reason else None
            if not execute_url(
                update_todo(
                    id=item_id,
                    canceled=True,
                    append_notes=f"\n{note}" if note else None,
                )
            ):
                raise ToolError(
                    "Could not confirm delivery. Check Things before retrying."
                )
            invalidate_caches_for(
                ["get-tasks", "get-inbox", "get-today", "get-anytime"]
            )

            def canceled():
                current = things.get(item_id) or {}
                return current.get("status") == "canceled" and (
                    not note or note in (current.get("notes") or "")
                )

            if not observe(canceled):
                raise ToolError(
                    "Cancellation was submitted but not confirmed. Check Things before retrying."
                )
            return f"Task canceled. ID: `{item_id}`"

        return await asyncio.to_thread(cancel)

    @mcp.tool(name="trash-task", annotations=TOOL_ANNOTATIONS["trash-task"], timeout=20)
    async def trash_task(
        task_id: str | None = None,
        task_title: str | None = None,
        confirm: bool = False,
    ) -> str:
        """Move a to-do to Things Trash. Requires explicit confirmation and a unique target."""
        if not get_settings().things_mcp_allow_automation_writes:
            raise ToolError(
                "Enable THINGS_MCP_ALLOW_AUTOMATION_WRITES to use this tool."
            )
        if not confirm:
            raise ToolError(
                "Confirm the exact task with the user before setting confirm=true."
            )

        def trash():
            task = _find_task(task_id, task_title, exact=True)
            item_id = task["uuid"]
            escaped_id = escape_applescript_string(item_id)
            result = run_applescript(
                'tell application id "com.culturedcode.ThingsMac"\n'
                f'  delete to do id "{escaped_id}"\n'
                "end tell"
            )
            invalidate_caches_for(
                ["get-tasks", "get-inbox", "get-today", "get-anytime"]
            )
            if result is False or not observe(
                lambda: (things.get(item_id) or {}).get("trashed")
            ):
                raise ToolError(
                    "Trash move was not confirmed. Check Things and macOS Automation permission before retrying."
                )
            return f"Task moved to Trash. ID: `{item_id}`"

        return await asyncio.to_thread(trash)

    @mcp.tool(
        name="create-area", annotations=TOOL_ANNOTATIONS["create-area"], timeout=30
    )
    async def create_area(title: str, tags: list[str] | None = None) -> str:
        """Create an area, or return the ID of an existing area with the same name."""
        if not get_settings().things_mcp_allow_automation_writes:
            raise ToolError(
                "Enable THINGS_MCP_ALLOW_AUTOMATION_WRITES to use this tool."
            )
        title = title.strip()
        if not title:
            raise ToolError("Provide an area title.")

        def create():
            with _area_lock:
                matches = [
                    area
                    for area in things.areas()
                    if area["title"].strip().casefold() == title.casefold()
                ]
                if len(matches) > 1:
                    raise ToolError("Multiple existing areas have that name.")
                if matches:
                    return f"Area already exists. ID: `{matches[0]['uuid']}`"
                if tags:
                    prepare_tags(tags)
                script = [
                    'tell application id "com.culturedcode.ThingsMac"',
                    f'  set newArea to make new area with properties {{name:"{escape_applescript_string(title)}"}}',
                ]
                if tags:
                    script.append(
                        f'  set tag names of newArea to "{escape_applescript_string(",".join(tags))}"'
                    )
                script.extend(["  return id of newArea", "end tell"])
                item_id = run_applescript("\n".join(script))
                invalidate_caches_for(["get-areas", "get-projects", "get-tasks"])

                def area_exists():
                    return any(area["uuid"] == item_id for area in things.areas())

                if not item_id or not observe(area_exists):
                    raise ToolError(
                        "Area creation was not confirmed. Check Things and macOS Automation permission before retrying."
                    )
                return f"Area created. ID: `{item_id}`"

        return await asyncio.to_thread(create)

    async def things_health() -> str:
        """Check Things database access and report configured write capabilities."""
        try:
            await asyncio.to_thread(things.inbox, count_only=True)
            database = "readable"
        except Exception:
            database = "unavailable. Check the launcher's macOS permission."
        settings = get_settings()
        return "\n".join(
            [
                f"Things database: {database}",
                f"Things URL token: {'configured' if get_things_auth_token() else 'unset'}",
                f"AppleScript tools: {'enabled' if settings.things_mcp_allow_automation_writes else 'disabled'}",
                f"AppleScript tag creation: {'enabled' if settings.things_mcp_allow_tag_creation else 'disabled'}",
            ]
        )

    for name in ("things-health", "diagnose"):
        mcp.tool(name=name, annotations=TOOL_ANNOTATIONS[name], timeout=10)(
            things_health
        )
