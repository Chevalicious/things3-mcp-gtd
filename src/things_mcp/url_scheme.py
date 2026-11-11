import json
import logging
import platform
import re
import subprocess
import urllib.parse
from enum import Enum, auto
from threading import Lock
from typing import Any, Dict, Optional, Union
from .utils import circuit_breaker, rate_limiter

logger = logging.getLogger(__name__)
_dispatch_lock = Lock()


# `when` values that carry a date and can therefore hold a timed reminder.
# Things expresses a reminder as a time component on the `when` date
# (e.g. `today@18:00`), NOT as a separate URL parameter. `anytime`, `someday`,
# and `evening` have no attachable clock time.
_DATE_ONLY_WHEN = {"today", "tomorrow"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_24H_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_TIME_12H_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([ap]m)$")


def _normalize_reminder_time(value: str) -> str:
    """Normalize a reminder time to Things' 24-hour ``HH:MM`` form.

    Accepts ``"6pm"``, ``"6:30pm"``, ``"18:00"``, ``"14:30"``. Bare hours without
    am/pm or a colon (e.g. ``"6"``) are rejected as ambiguous.

    Raises:
        ValueError: If the time cannot be parsed.
    """
    raw = value.strip().lower()

    m = _TIME_12H_RE.match(raw)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        meridiem = m.group(3)
        if not (1 <= hour <= 12) or not (0 <= minute <= 59):
            raise ValueError(f"Invalid reminder time: {value!r}")
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    m = _TIME_24H_RE.match(raw)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError(f"Invalid reminder time: {value!r}")
        return f"{hour:02d}:{minute:02d}"

    raise ValueError(
        f"Could not parse reminder time {value!r}. "
        "Use forms like '6pm', '6:30pm', '18:00', or '14:30'."
    )


def _is_date_like_when(when: str) -> bool:
    """True if ``when`` is a value that can carry a timed reminder."""
    return when in _DATE_ONLY_WHEN or bool(_DATE_RE.match(when))


def build_when_with_reminder(
    when: Optional[str],
    reminder_time: Optional[str] = None,
    reminder_at: Optional[str] = None,
) -> Optional[str]:
    """Compose a Things ``when`` value with an optional timed reminder.

    Things has no standalone reminder parameter. A reminder is a time component on
    the ``when`` date using ``when=<date>@<time>`` (e.g. ``today@18:00``,
    ``2026-06-10@14:30``). This helper composes that string.

    Args:
        when: Base schedule — ``today``, ``tomorrow``, or ``YYYY-MM-DD``. Reminders
            are only valid on these date-like values, NOT ``anytime``/``someday``/
            ``evening``.
        reminder_time: Time to attach to ``when`` (e.g. ``"6pm"``, ``"18:00"``).
        reminder_at: Pre-composed ``"<date>@<time>"`` string; used as the full
            ``when`` value (takes precedence over ``when`` + ``reminder_time``).

    Returns:
        The composed ``when`` string, or the original ``when`` if no reminder was
        requested.

    Raises:
        ValueError: If a reminder is requested on a non-dated ``when``, if both
            ``reminder_at`` and ``reminder_time`` are supplied, or if a time/date
            component is malformed.
    """
    if reminder_at and reminder_time:
        raise ValueError(
            "Provide either reminder_at (a full 'date@time') or reminder_time "
            "(combined with 'when'), not both."
        )

    if reminder_at:
        if "@" not in reminder_at:
            raise ValueError(
                f"reminder_at must be a 'date@time' string (e.g. '2026-06-10@14:30'), "
                f"got {reminder_at!r}."
            )
        date_part, time_part = reminder_at.split("@", 1)
        date_part = date_part.strip()
        if not _is_date_like_when(date_part):
            raise ValueError(
                f"reminder_at date must be 'today', 'tomorrow', or YYYY-MM-DD, "
                f"got {date_part!r}."
            )
        return f"{date_part}@{_normalize_reminder_time(time_part)}"

    if reminder_time:
        if not when or not _is_date_like_when(when):
            raise ValueError(
                f"reminder_time requires a date-like 'when' (today, tomorrow, or "
                f"YYYY-MM-DD). Reminders cannot be attached to {when!r}. "
                "Use 'deadline' for a hard due date instead."
            )
        return f"{when}@{_normalize_reminder_time(reminder_time)}"

    return when


class DispatchOutcome(Enum):
    UNSENT = auto()
    UNCERTAIN = auto()
    HANDED_OFF = auto()


def _open_url_background(url: str, timeout: float) -> DispatchOutcome:
    """Hand a Things URL to macOS without using a shell."""
    if platform.system() != "Darwin":
        return DispatchOutcome.UNSENT

    try:
        result = subprocess.run(
            ["/usr/bin/open", "-g", "-b", "com.culturedcode.ThingsMac", url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except OSError:
        return DispatchOutcome.UNSENT
    except subprocess.TimeoutExpired:
        logger.warning("Could not confirm delivery of the Things command")
        return DispatchOutcome.UNCERTAIN

    return (
        DispatchOutcome.HANDED_OFF
        if result.returncode == 0
        else DispatchOutcome.UNCERTAIN
    )


def dispatch_url(url: str, timeout: float = 5.0) -> DispatchOutcome:
    """Dispatch once, distinguishing a blocked send from uncertain delivery."""
    if not url.startswith("things:///") or not _dispatch_lock.acquire(timeout=2):
        return DispatchOutcome.UNSENT
    try:
        if not circuit_breaker.allow_operation():
            return DispatchOutcome.UNSENT
        rate_limiter.wait_if_needed()
        outcome = _open_url_background(url.replace("+", "%20"), timeout)
        if outcome is DispatchOutcome.HANDED_OFF:
            circuit_breaker.record_success()
        else:
            circuit_breaker.record_failure()
        return outcome
    finally:
        _dispatch_lock.release()


def execute_url(url: str, timeout: float = 5.0) -> bool:
    """Dispatch once. Successful delivery does not confirm that Things applied it."""
    return dispatch_url(url, timeout) is DispatchOutcome.HANDED_OFF


def construct_url(command: str, params: Dict[str, Any]) -> str:
    """Construct a Things URL from command and parameters."""
    # Use parameters as provided. urllib.parse.quote will handle encoding of
    # spaces and literal plus signs correctly (" " -> "%20", "+" -> "%2B").

    # Start with base URL
    url = f"things:///{command}"

    if command in {"update", "update-project"}:
        from .config import get_things_auth_token
        from fastmcp.exceptions import ToolError

        token = get_things_auth_token()
        if not token:
            raise ToolError(
                "Set THINGS_AUTH_TOKEN before updating existing Things items."
            )
        params = {**params, "auth-token": token}

    # Standard URL scheme encoding
    if params:
        encoded_params = []
        for key, value in params.items():
            if value is None:
                continue
            # Handle boolean values
            if isinstance(value, bool):
                value = str(value).lower()
            # Handle lists (for tags, checklist items etc)
            elif isinstance(value, list) and key == "tags":
                # Important: Tags are sensitive to formatting in Things URL scheme
                # Based on testing, using a simple comma-separated list without spaces works best
                encoded_tags = []
                for tag in value:
                    # Ensure tag is properly encoded as string
                    tag_str = str(tag).strip()
                    if tag_str:  # Only add non-empty tags
                        encoded_tags.append(tag_str)

                # Only include non-empty tag lists
                if encoded_tags or not value:
                    # Join with commas - Things expects comma-separated tags without spaces between commas
                    # Use a simple comma with no spacing for maximum compatibility
                    value = ",".join(encoded_tags)
                else:
                    # If no valid tags, don't include this parameter
                    continue
            # Handle other lists
            elif isinstance(value, list):
                value = ",".join(str(v) for v in value)

            # Encode the value. urllib.parse.quote will encode spaces as %20 and
            # preserve literal plus signs by converting them to %2B.
            encoded_value = urllib.parse.quote(str(value), safe="")
            encoded_params.append(f"{key}={encoded_value}")

        url += "?" + "&".join(encoded_params)

    return url


def add_todo(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[list[str]] = None,
    checklist_items: Optional[list[str]] = None,
    list_id: Optional[str] = None,
    list_title: Optional[str] = None,
    heading: Optional[str] = None,
    completed: Optional[bool] = None,
) -> str:
    """Construct URL to add a new todo."""
    params = {
        "title": title,
        "notes": notes,
        "when": when,
        "deadline": deadline,
        "checklist-items": "\n".join(checklist_items)
        if checklist_items is not None
        else None,
        "list-id": list_id,
        "list": list_title,
        "heading": heading,
        "completed": completed,
    }

    # Handle tags separately since they need to be comma-separated
    if tags:
        params["tags"] = ",".join(tags)
    return construct_url("add", {k: v for k, v in params.items() if v is not None})


def add_project(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[list[str]] = None,
    area_id: Optional[str] = None,
    area_title: Optional[str] = None,
    todos: Optional[list[str]] = None,
) -> str:
    """Construct URL to add a new project."""
    params = {
        "title": title,
        "notes": notes,
        "when": when,
        "deadline": deadline,
        "area-id": area_id,
        "area": area_title,
        # Change todos to be newline separated
        "to-dos": "\n".join(todos) if todos else None,
    }

    # Handle tags separately since they need to be comma-separated
    if tags:
        params["tags"] = ",".join(tags)

    return construct_url(
        "add-project", {k: v for k, v in params.items() if v is not None}
    )


def update_todo(
    id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    prepend_notes: Optional[str] = None,
    append_notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[Union[list[str], str]] = None,
    add_tags: Optional[Union[list[str], str]] = None,
    checklist_items: Optional[list[str]] = None,
    prepend_checklist_items: Optional[list[str]] = None,
    append_checklist_items: Optional[list[str]] = None,
    completed: Optional[bool] = None,
    canceled: Optional[bool] = None,
    list_id: Optional[str] = None,
    heading_id: Optional[str] = None,
) -> str:
    """Construct URL to update an existing todo.

    Args:
        id: The UUID of the todo to update
        title: New title (replaces existing)
        notes: New notes (replaces existing)
        prepend_notes: Text to add before existing notes
        append_notes: Text to add after existing notes
        when: Schedule date (today, tomorrow, evening, anytime, someday, or YYYY-MM-DD)
        deadline: Deadline date (YYYY-MM-DD)
        tags: Tags to set (replaces existing)
        add_tags: Tags to add without replacing existing ones
        checklist_items: Checklist items (replaces existing)
        prepend_checklist_items: Items to add at beginning of checklist
        append_checklist_items: Items to add at end of checklist
        completed: Mark as completed
        canceled: Mark as canceled
        list_id: ID of the destination project or area
        heading_id: ID of a heading within the destination project
    """
    params = {
        "id": id,
        "title": title,
        "notes": notes,
        "prepend-notes": prepend_notes,
        "append-notes": append_notes,
        "when": when,
        "deadline": deadline,
        "tags": tags,
        "add-tags": add_tags,
        "checklist-items": "\n".join(checklist_items)
        if checklist_items is not None
        else None,
        "prepend-checklist-items": "\n".join(prepend_checklist_items)
        if prepend_checklist_items
        else None,
        "append-checklist-items": "\n".join(append_checklist_items)
        if append_checklist_items
        else None,
        "completed": completed,
        "canceled": canceled,
        "list-id": list_id,
        "heading-id": heading_id,
    }
    return construct_url("update", {k: v for k, v in params.items() if v is not None})


def update_project(
    id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    prepend_notes: Optional[str] = None,
    append_notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[Union[list[str], str]] = None,
    add_tags: Optional[Union[list[str], str]] = None,
    completed: Optional[bool] = None,
    canceled: Optional[bool] = None,
) -> str:
    """Construct URL to update an existing project.

    Args:
        id: The UUID of the project to update
        title: New title (replaces existing)
        notes: New notes (replaces existing)
        prepend_notes: Text to add before existing notes
        append_notes: Text to add after existing notes
        when: Schedule date
        deadline: Deadline date
        tags: Tags to set (replaces existing)
        add_tags: Tags to add without replacing existing ones
        completed: Mark as completed
        canceled: Mark as canceled
    """
    params = {
        "id": id,
        "title": title,
        "notes": notes,
        "prepend-notes": prepend_notes,
        "append-notes": append_notes,
        "when": when,
        "deadline": deadline,
        "tags": tags,
        "add-tags": add_tags,
        "completed": completed,
        "canceled": canceled,
    }
    return construct_url(
        "update-project", {k: v for k, v in params.items() if v is not None}
    )


def show(
    id: str, query: Optional[str] = None, filter_tags: Optional[list[str]] = None
) -> str:
    """Construct URL to show a specific item or list."""
    params = {"id": id, "query": query, "filter": filter_tags}
    return construct_url("show", {k: v for k, v in params.items() if v is not None})


def search(query: str) -> str:
    """Construct URL to perform a search."""
    return construct_url("search", {"query": query})


# =============================================================================
# JSON API Support for Bulk Operations
# =============================================================================


def build_todo_object(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[list[str]] = None,
    checklist_items: Optional[list[Dict[str, Any]]] = None,
    list_id: Optional[str] = None,
    heading: Optional[str] = None,
    heading_id: Optional[str] = None,
    completed: Optional[bool] = None,
    canceled: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build a to-do object for the JSON API.

    Args:
        title: Task title (required)
        notes: Task notes
        when: Schedule (today, tomorrow, evening, anytime, someday, or date)
        deadline: Deadline date
        tags: List of tag names
        checklist_items: List of checklist item dicts with 'title' and optional 'completed'
        list_id: UUID of project to add to
        heading: Name of heading within project
        heading_id: UUID of heading within project
        completed: Mark as completed
        canceled: Mark as canceled

    Returns:
        Dict suitable for Things JSON API
    """
    attributes: Dict[str, Any] = {"title": title}

    if notes is not None:
        attributes["notes"] = notes
    if when is not None:
        attributes["when"] = when
    if deadline is not None:
        attributes["deadline"] = deadline
    if tags:
        attributes["tags"] = tags
    if checklist_items:
        attributes["checklist-items"] = checklist_items
    if list_id is not None:
        attributes["list-id"] = list_id
    if heading is not None:
        attributes["heading"] = heading
    if heading_id is not None:
        attributes["heading-id"] = heading_id
    if completed is not None:
        attributes["completed"] = completed
    if canceled is not None:
        attributes["canceled"] = canceled

    return {"type": "to-do", "attributes": attributes}


def build_project_object(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[list[str]] = None,
    area_id: Optional[str] = None,
    area: Optional[str] = None,
    items: Optional[list[Dict[str, Any]]] = None,
    completed: Optional[bool] = None,
    canceled: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build a project object for the JSON API.

    Args:
        title: Project title (required)
        notes: Project notes
        when: Schedule
        deadline: Deadline date
        tags: List of tag names
        area_id: UUID of area to add to
        area: Name of area to add to
        items: List of to-do or heading objects to include in project
        completed: Mark as completed
        canceled: Mark as canceled

    Returns:
        Dict suitable for Things JSON API
    """
    attributes: Dict[str, Any] = {"title": title}

    if notes is not None:
        attributes["notes"] = notes
    if when is not None:
        attributes["when"] = when
    if deadline is not None:
        attributes["deadline"] = deadline
    if tags:
        attributes["tags"] = tags
    if area_id is not None:
        attributes["area-id"] = area_id
    if area is not None:
        attributes["area"] = area
    if items:
        attributes["items"] = items
    if completed is not None:
        attributes["completed"] = completed
    if canceled is not None:
        attributes["canceled"] = canceled

    return {"type": "project", "attributes": attributes}


def build_heading_object(title: str, archived: Optional[bool] = None) -> Dict[str, Any]:
    """Build a heading object for the JSON API.

    Args:
        title: Heading title
        archived: Whether the heading is archived

    Returns:
        Dict suitable for Things JSON API
    """
    attributes: Dict[str, Any] = {"title": title}
    if archived is not None:
        attributes["archived"] = archived
    return {"type": "heading", "attributes": attributes}


def build_checklist_item(
    title: str, completed: Optional[bool] = None, canceled: Optional[bool] = None
) -> Dict[str, Any]:
    """Build a checklist item object for the JSON API.

    Args:
        title: Checklist item title
        completed: Whether the item is completed
        canceled: Whether the item is canceled

    Returns:
        Dict suitable for Things JSON API
    """
    attributes: Dict[str, Any] = {"title": title}
    if completed is not None:
        attributes["completed"] = completed
    if canceled is not None:
        attributes["canceled"] = canceled
    return {"type": "checklist-item", "attributes": attributes}


def construct_json_url(items: list[Dict[str, Any]]) -> str:
    """Construct a Things JSON URL for bulk operations.

    Args:
        items: List of to-do, project, or heading objects

    Returns:
        URL string for the Things JSON API
    """
    # Serialize to JSON and URL-encode
    json_data = json.dumps(items, separators=(",", ":"))  # Compact JSON
    encoded_data = urllib.parse.quote(json_data, safe="")

    # Build URL
    url = f"things:///json?data={encoded_data}"
    logger.debug(f"Constructed JSON URL with {len(items)} items")
    return url


def add_project_with_tasks(
    title: str,
    tasks: list[Dict[str, Any]],
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[list[str]] = None,
    area: Optional[str] = None,
    area_id: Optional[str] = None,
    headings: Optional[Dict[str, list[Dict[str, Any]]]] = None,
) -> str:
    """Construct one JSON request to create a project with its initial tasks.

    Args:
        title: Project title
        tasks: List of task dicts with 'title' and optional other fields
        notes: Project notes
        when: Project schedule
        deadline: Project deadline
        tags: Project tags
        area: Area name to add project to
        area_id: Area UUID to add project to
        headings: Dict mapping heading names to lists of tasks under that heading

    Returns:
        URL string for the Things JSON API
    """

    def build_task(task):
        return build_todo_object(
            title=task.get("title", ""),
            notes=task.get("notes"),
            when=task.get("when"),
            deadline=task.get("deadline"),
            tags=task.get("tags"),
            checklist_items=[
                build_checklist_item(item) if isinstance(item, str) else item
                for item in (task.get("checklist_items") or [])
            ],
        )

    items = [build_task(task) for task in tasks]
    # Things assigns to-dos to the most recent heading in this array.
    for heading_name, heading_tasks in (headings or {}).items():
        items.append(build_heading_object(heading_name))
        items.extend(build_task(task) for task in heading_tasks)

    # Build the project object with all items
    project = build_project_object(
        title=title,
        notes=notes,
        when=when,
        deadline=deadline,
        tags=tags,
        area=area,
        area_id=area_id,
        items=items,
    )

    return construct_json_url([project])
