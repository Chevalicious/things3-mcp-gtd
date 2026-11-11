"""Bounded readback after sending a write to Things."""

import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from threading import Lock

from fastmcp.exceptions import ToolError

from .url_scheme import DispatchOutcome

_creation_lock = Lock()
_UNCONFIRMED = "Check Things before retrying."


def observe(read: Callable[[], object], timeout: float = 2.5):
    """Poll fresh reads briefly. A failed read does not undo a dispatched write."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            if value := read():
                return value
        except Exception:
            return None
        if (remaining := deadline - time.monotonic()) <= 0:
            return None
        time.sleep(min(0.15, remaining))


def create_and_observe(
    dispatch: Callable[[str], bool],
    url: str,
    lookup: Callable[[], Iterable[dict]],
    title: str,
    matches: Callable[[dict], bool],
) -> str | None:
    """Find one new matching ID, excluding IDs present before the write.

    Serialize this window within the server. External writers are not locked;
    this is database readback, not an app-issued callback.
    """

    def candidates():
        return {
            item["uuid"]
            for item in lookup()
            if item.get("uuid")
            and item.get("title") == title
            and not item.get("trashed")
        }

    if not _creation_lock.acquire(timeout=5):
        raise ToolError("Another creation is still being checked. Try again shortly.")
    try:
        try:
            before = candidates()
        except Exception:
            before = None
        if not dispatch(url):
            raise ToolError(f"Could not confirm delivery to Things. {_UNCONFIRMED}")
        if before is None:
            return None

        def read():
            return {
                item["uuid"]
                for item in lookup()
                if item.get("uuid")
                and item["uuid"] not in before
                and item.get("title") == title
                and not item.get("trashed")
                and matches(item)
            }

        found = observe(read)
        return next(iter(found)) if found and len(found) == 1 else None
    finally:
        _creation_lock.release()


def observe_inbox_batch(
    dispatch: Callable[[str], DispatchOutcome],
    url: str,
    snapshot: Callable[[], Iterable[dict]],
    lookup: Callable[[], Iterable[dict]],
    expected: list[tuple],
    content: Callable[[dict], tuple],
) -> list[str | None]:
    """Observe a single dispatch while holding the same guard as other creates."""
    if not _creation_lock.acquire(timeout=5):
        raise ToolError("Another creation is still being checked. Try again shortly.")
    try:
        try:
            before = {item["uuid"] for item in snapshot()}
        except Exception:
            raise ToolError(
                "Could not read Things before sending. Check database access."
            ) from None

        try:
            outcome = dispatch(url)
        except Exception:
            outcome = DispatchOutcome.UNCERTAIN
        if outcome is DispatchOutcome.UNSENT:
            raise ToolError(
                "The URL was blocked before delivery. Check that Things is available and try again."
            )
        if outcome is DispatchOutcome.UNCERTAIN:
            return [None] * len(expected)

        counts = Counter(expected)
        observed = defaultdict(set)
        seen_content = defaultdict(set)

        def read():
            for item in lookup():
                item_id = item.get("uuid")
                if not item_id or item_id in before or item.get("trashed"):
                    continue
                signature = content(item)
                seen_content[item_id].add(signature)
                if signature in counts:
                    observed[signature].add(item_id)
            # Watch the full window for late arrivals with the same content.
            return False

        observe(read)
        confirmed = {}
        for signature, ids in observed.items():
            if counts[signature] == 1 and len(ids) == 1:
                item_id = next(iter(ids))
                if len(seen_content[item_id]) == 1:
                    confirmed[signature] = item_id
        return [confirmed.get(signature) for signature in expected]
    finally:
        _creation_lock.release()


def creation_result(label: str, title: str, item_id: str | None) -> str:
    if item_id:
        return f"{label}: {title}\nID: `{item_id}`"
    return f"{label} request submitted: {title}\nCreation was not confirmed. {_UNCONFIRMED}"
