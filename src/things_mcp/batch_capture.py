"""Preflight and receipts for a create-only Inbox batch."""

from collections.abc import Mapping
from typing import Annotated, Any

import things
from fastmcp.exceptions import ToolError
from pydantic import WithJsonSchema

from .cache import invalidate_caches_for
from .tag_handler import existing_tag_names, missing_tags
from .url_scheme import build_todo_object, construct_json_url, dispatch_url
from .write_confirmation import observe_inbox_batch

MAX_ROWS = 10
MAX_URL_BYTES = 16_384
MAX_TITLE_LENGTH = 512
MAX_NOTES_LENGTH = 10_000

# Validate inside the tool so malformed input gets an actionable row receipt
# without passing the submitted text through framework validation diagnostics.
CaptureRows = Annotated[
    Any,
    WithJsonSchema(
        {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ROWS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title"],
                "properties": {
                    "title": {"type": "string", "maxLength": MAX_TITLE_LENGTH},
                    "notes": {"type": "string", "maxLength": MAX_NOTES_LENGTH},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    ),
]


def _row_error(count: int, row: int, reason: str) -> str:
    return "\n".join(
        f"{number}. Unsent — {reason if number == row else f'Fix row {row} before submitting the batch.'}"
        for number in range(1, count + 1)
    )


def _validate_row(row: Any) -> str | None:
    if not isinstance(row, dict) or row.keys() - {"title", "notes", "tags"}:
        return "Provide an object with title and optional notes or tags only."
    title = row.get("title")
    if not isinstance(title, str) or not title.strip() or title.splitlines() != [title]:
        return "Provide a nonempty, single-line title."
    if len(title) > MAX_TITLE_LENGTH:
        return f"Shorten the title to {MAX_TITLE_LENGTH} characters or fewer."
    notes = row.get("notes", "")
    if not isinstance(notes, str) or len(notes) > MAX_NOTES_LENGTH:
        return f"Provide notes as text of at most {MAX_NOTES_LENGTH:,} characters, or omit notes."
    tags = row.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        return "Provide tags as an array of existing tag names, or omit tags."
    for value in (title, notes, *tags):
        if "\x00" in value:
            return "Remove null characters from the text."
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return "Replace invalid Unicode characters with valid text."
    return None


def capture_batch(rows: Any) -> str:
    if not isinstance(rows, list) or not rows:
        return "Unsent — provide a tasks array with 1 to 10 task objects."
    if len(rows) > MAX_ROWS:
        return f"Rows 1–{len(rows)}. Unsent — row {MAX_ROWS + 1} exceeds the batch limit. Split into batches of at most {MAX_ROWS} tasks."

    items = []
    known_tags = None
    for number, row in enumerate(rows, 1):
        if error := _validate_row(row):
            return _row_error(len(rows), number, error)
        tags = row.get("tags", [])
        try:
            if tags:
                if known_tags is None:
                    known_tags = existing_tag_names()
                if missing_tags(tags, known_tags):
                    return _row_error(
                        len(rows),
                        number,
                        "Use existing Things tags from get-tags, or remove the unknown tags.",
                    )
                tags = list(dict.fromkeys(known_tags[tag.casefold()] for tag in tags))
        except ToolError as exc:
            return _row_error(len(rows), number, str(exc))
        except Exception:
            return _row_error(
                len(rows),
                number,
                "Could not read tags. Check Things and database access.",
            )
        items.append(build_todo_object(row["title"], notes=row.get("notes"), tags=tags))
        url = construct_json_url(items)
        if len(url) > MAX_URL_BYTES:
            return _row_error(
                len(rows),
                number,
                f"The encoded URL exceeds {MAX_URL_BYTES:,} bytes at this row. Shorten the text or split the batch.",
            )

    expected = [_content(item["attributes"]) for item in items]
    try:
        confirmed = observe_inbox_batch(
            dispatch_url,
            url,
            snapshot=lambda: things.todos(
                status=None, trashed=None, context_trashed=None
            ),
            lookup=lambda: things.inbox(status=None, type="to-do"),
            expected=expected,
            content=_content,
        )
    except ToolError as exc:
        return "\n".join(f"{n}. Unsent — {exc}" for n in range(1, len(rows) + 1))

    invalidate_caches_for(["get-inbox", "get-tasks"])
    return "\n".join(
        f"{number}. Confirmed — ID: `{item_id}`"
        if item_id
        else f"{number}. Unconfirmed — check Things before retrying this row."
        for number, item_id in enumerate(confirmed, 1)
    )


def _content(item: Mapping) -> tuple:
    return (
        item["title"],
        item.get("notes") or "",
        frozenset(tag.casefold() for tag in item.get("tags") or []),
    )
