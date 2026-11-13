import json
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from fastmcp import Client

from things_mcp import batch_capture, write_confirmation
from things_mcp.fast_server import mcp
from things_mcp.url_scheme import DispatchOutcome


@pytest.fixture
def boundary(monkeypatch):
    dispatch = Mock(return_value=DispatchOutcome.HANDED_OFF)
    snapshot = Mock(return_value=[])
    inbox = Mock(return_value=[])
    monkeypatch.setattr(batch_capture, "dispatch_url", dispatch)
    monkeypatch.setattr(batch_capture.things, "todos", snapshot)
    monkeypatch.setattr(batch_capture.things, "inbox", inbox)
    monkeypatch.setattr(
        write_confirmation,
        "time",
        SimpleNamespace(monotonic=Mock(side_effect=[0, 1, 3]), sleep=Mock()),
    )
    return dispatch, snapshot, inbox


async def call_batch(rows):
    async with Client(mcp) as client:
        result = await client.call_tool("capture-tasks", {"tasks": rows})
    assert not result.is_error
    assert result.structured_content is None
    return result.content[0].text


async def test_batch_sends_once_and_matches_distinct_rows_in_input_order(
    boundary, monkeypatch
):
    dispatch, snapshot, inbox = boundary
    monkeypatch.setattr(batch_capture.things, "tags", lambda: [{"title": "Desk"}])
    old = {"uuid": "old", "title": "Call", "notes": "A + & café", "tags": ["Desk"]}
    snapshot.return_value = [old]
    first = {**old, "uuid": "new-a"}
    second = {"uuid": "new-b", "title": "Call", "notes": "B"}
    inbox.return_value = [old, second, first]

    result = await call_batch(
        [
            {"title": "Call", "notes": "A + & café", "tags": ["desk"]},
            {"title": "Call", "notes": "B"},
        ]
    )
    assert result.splitlines() == [
        "1. Confirmed — ID: `new-a`",
        "2. Confirmed — ID: `new-b`",
    ]
    dispatch.assert_called_once()
    url = urlsplit(dispatch.call_args.args[0])
    assert url.scheme == "things" and url.path == "/json"
    query = parse_qs(url.query)
    assert set(query) == {"data"}
    assert json.loads(query["data"][0]) == [
        {
            "type": "to-do",
            "attributes": {"title": "Call", "notes": "A + & café", "tags": ["Desk"]},
        },
        {"type": "to-do", "attributes": {"title": "Call", "notes": "B"}},
    ]


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ("bad", "Provide an object"),
        ({"title": "\n"}, "single-line title"),
        ({"title": "a" * 513}, "Shorten the title"),
        ({"title": "Bad", "tags": [1]}, "Provide tags as an array"),
        ({"title": "Bad", "tags": ["Missing"]}, "Use existing Things tags"),
        ({"title": "Bad", "notes": "🥭" * 1600}, "encoded URL exceeds"),
    ],
)
async def test_invalid_batch_leaves_all_rows_unsent(boundary, monkeypatch, row, reason):
    dispatch, snapshot, _ = boundary
    monkeypatch.setenv("THINGS_MCP_ALLOW_TAG_CREATION", "true")
    monkeypatch.setattr(batch_capture.things, "tags", lambda: [])
    create_tag = Mock()
    monkeypatch.setattr("things_mcp.tag_handler.run_applescript", create_tag)
    result = await call_batch([{"title": "OK"}, row])
    assert "1. Unsent — Fix row 2" in result
    assert result.splitlines()[1].startswith("2. Unsent — ")
    assert reason in result.splitlines()[1]
    dispatch.assert_not_called()
    snapshot.assert_not_called()
    create_tag.assert_not_called()


async def test_batch_with_identical_rows_and_late_ambiguity_keeps_partial_success(
    boundary,
):
    dispatch, _, inbox = boundary
    unique = {"uuid": "unique-id", "title": "Unique"}
    conflict = {"uuid": "external-1", "title": "Ambiguous"}
    reused = {"uuid": "reused", "title": "Before edit"}
    inbox.side_effect = [
        [unique, conflict, reused, {"uuid": "one-copy", "title": "Same"}],
        [
            unique,
            conflict,
            {**conflict, "uuid": "external-2"},
            {**reused, "title": "After edit"},
        ],
    ]
    result = await call_batch(
        [
            {"title": title}
            for title in [
                "Same",
                "Same",
                "Unique",
                "Ambiguous",
                "Before edit",
                "After edit",
            ]
        ]
    )
    assert result.count("Unconfirmed") == 5
    assert result.count("check Things before retrying this row") == 5
    assert "3. Confirmed — ID: `unique-id`" in result
    assert (
        "reused" not in result
        and "one-copy" not in result
        and "external-" not in result
    )
    dispatch.assert_called_once()


async def test_batch_retains_visible_row_if_next_read_fails(boundary):
    dispatch, _, inbox = boundary
    inbox.side_effect = [
        [{"uuid": "new", "title": "First"}],
        OSError("private details"),
    ]
    result = await call_batch([{"title": "First"}, {"title": "Second"}])
    assert "1. Confirmed — ID: `new`" in result
    assert "2. Unconfirmed" in result
    assert "private details" not in result
    dispatch.assert_called_once()


@pytest.mark.parametrize(
    ("outcome", "receipt"),
    [
        (DispatchOutcome.UNSENT, "Unsent"),
        (DispatchOutcome.UNCERTAIN, "Unconfirmed"),
        (TimeoutError("private URL"), "Unconfirmed"),
    ],
)
async def test_batch_dispatch_outcomes_never_replay(boundary, outcome, receipt):
    dispatch, _, inbox = boundary
    if isinstance(outcome, Exception):
        dispatch.side_effect = outcome
    else:
        dispatch.return_value = outcome
    assert f"1. {receipt}" in await call_batch([{"title": "Item"}])
    dispatch.assert_called_once()
    inbox.assert_not_called()


async def test_failed_snapshot_prevents_dispatch(boundary):
    dispatch, snapshot, inbox = boundary
    snapshot.side_effect = OSError("private details")
    assert "1. Unsent — Could not read Things" in await call_batch([{"title": "Item"}])
    dispatch.assert_not_called()
    inbox.assert_not_called()
