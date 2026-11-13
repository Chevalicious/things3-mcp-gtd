"""Exercise tool behavior through MCP with the Things boundary mocked."""

from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from fastmcp import Client

from things_mcp import tools_planning, tools_reviews, tools_tasks, tools_utility
from things_mcp.fast_server import mcp


async def test_search_applies_keyword_and_filters_together(monkeypatch):
    search = Mock(return_value=[])
    monkeypatch.setattr(tools_utility.things, "search", search)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search-tasks", {"query": "call", "tag": "phone", "status": "completed"}
        )
    assert not result.is_error
    search.assert_called_once_with("call", tag="phone", status="completed")


async def test_schedule_resolves_area_and_rejects_ambiguous_name(monkeypatch):
    areas = Mock(return_value=[{"uuid": "area-id", "title": "Home"}])
    dispatch = Mock(return_value=True)
    monkeypatch.setattr(tools_planning.things, "areas", areas)
    monkeypatch.setattr(
        tools_planning.things,
        "todos",
        Mock(
            side_effect=[
                [],
                [{"uuid": "new", "title": "Check list", "area": "area-id"}],
            ]
        ),
    )
    monkeypatch.setattr(tools_planning, "execute_url", dispatch)
    async with Client(mcp) as client:
        args = {"title": "Check list", "when": "today", "area": "Home"}
        created = await client.call_tool("schedule-task", args)
        assert "ID: `new`" in created.content[0].text
        assert parse_qs(urlsplit(dispatch.call_args.args[0]).query)["list-id"] == [
            "area-id"
        ]
        areas.return_value.append({"uuid": "another-id", "title": "Home"})
        result = await client.call_tool("schedule-task", args, raise_on_error=False)
        assert result.is_error
    assert dispatch.call_count == 1


async def test_complete_submits_notes_and_completion_together(monkeypatch):
    monkeypatch.setattr("things_mcp.config.get_things_auth_token", lambda: "test-only")
    dispatch = Mock(return_value=True)
    monkeypatch.setattr(tools_tasks, "execute_url", dispatch)
    monkeypatch.setattr(
        tools_tasks.things,
        "get",
        lambda _: {"status": "completed", "notes": "[Completed] Done"},
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "complete-task", {"task_id": "abc", "completion_notes": "Done"}
        )
    assert "Task completed. ID: `abc`" in result.content[0].text
    assert dispatch.call_count == 1
    args = parse_qs(urlsplit(dispatch.call_args.args[0]).query)
    assert args["completed"] == ["true"]
    assert args["append-notes"] == ["\n[Completed] Done"]


async def test_conversion_leaves_original_if_project_is_not_observed(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    things = SimpleNamespace(
        get=Mock(return_value={"type": "to-do", "title": "Plan"}),
        checklist_items=Mock(return_value=[]),
        projects=Mock(return_value=[{"uuid": "old", "title": "Plan"}]),
    )
    monkeypatch.setattr(tools_tasks, "things", things)
    monkeypatch.setattr(
        tools_tasks,
        "asyncio",
        SimpleNamespace(
            to_thread=tools_tasks.asyncio.to_thread,
            sleep=AsyncMock(),
        ),
    )
    monkeypatch.setattr("things_mcp.config.get_things_auth_token", lambda: "test-only")
    dispatch = Mock(return_value=True)
    monkeypatch.setattr(tools_tasks, "execute_url", dispatch)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "convert-to-project", {"task_id": "abc"}, raise_on_error=False
        )
    assert result.is_error
    assert dispatch.call_count == 1
    assert dispatch.call_args.args[0].startswith("things:///json?")


async def test_weekly_review_uses_one_project_task_lookup(monkeypatch):
    from types import SimpleNamespace

    projects = [
        {"uuid": str(i), "title": f"Project {i}", "status": "incomplete"}
        for i in range(3)
    ]
    todos = Mock(
        side_effect=lambda **kw: (
            [
                {"project": "0", "start": "Anytime"},
                {"project": "1", "start": "Someday"},
            ]
            if kw.get("project")
            else []
        )
    )
    monkeypatch.setattr(
        tools_reviews,
        "things",
        SimpleNamespace(
            inbox=lambda **kwargs: 0,
            projects=lambda: projects,
            todos=todos,
            someday=lambda: [],
            last=lambda *a, **kw: [],
        ),
    )
    async with Client(mcp) as client:
        result = await client.call_tool("weekly-review", {})
    assert not result.is_error
    text = result.content[0].text
    assert "Project 0" not in text
    assert "Project 1" in text and "Project 2" in text
    assert [c.kwargs for c in todos.call_args_list if "project" in c.kwargs] == [
        {"project": True}
    ]


async def test_tags_do_not_request_automation_by_default(monkeypatch):
    from things_mcp import tag_handler
    from things_mcp.settings import Settings

    run_script = Mock(side_effect=AssertionError("AppleScript must not be called"))
    dispatch = Mock(return_value=True)
    monkeypatch.setattr(
        tag_handler,
        "get_settings",
        lambda: Settings(_env_file=None, things_mcp_allow_tag_creation=False),
    )
    monkeypatch.setattr(tag_handler.things, "tags", lambda: [{"title": "Existing"}])
    monkeypatch.setattr(tag_handler, "run_applescript", run_script)
    monkeypatch.setattr(tools_tasks.things, "inbox", Mock(side_effect=OSError))
    monkeypatch.setattr(tools_tasks, "execute_url", dispatch)

    async with Client(mcp) as client:
        missing = await client.call_tool(
            "capture-task", {"title": "Test", "tags": ["Missing"]}, raise_on_error=False
        )
        assert missing.is_error and "Create them in Things" in missing.content[0].text
        assert dispatch.call_count == 0
        for _ in range(3):
            existing = await client.call_tool(
                "capture-task", {"title": "Test", "tags": ["Existing"]}
            )
            assert not existing.is_error
    assert dispatch.call_count == 3
    run_script.assert_not_called()


async def test_move_uses_heading_parent_and_verifies_original_id(monkeypatch):
    monkeypatch.setattr("things_mcp.config.get_things_auth_token", lambda: "test-only")
    records = {
        "task": {"type": "to-do", "notes": "Keep me"},
        "section": {
            "type": "heading",
            "title": "Prep",
            "project": "project",
            "status": "incomplete",
        },
        "project": {"type": "project", "status": "incomplete"},
    }
    monkeypatch.setattr(tools_planning.things, "get", records.get)

    def dispatch(url):
        args = parse_qs(urlsplit(url).query)
        assert args["id"] == ["task"]
        assert args["heading-id"] == ["section"]
        assert args["list-id"] == ["project"]
        assert "notes" not in args
        records["task"]["heading"] = "section"
        return True

    send = Mock(side_effect=dispatch)
    monkeypatch.setattr(tools_planning, "execute_url", send)
    async with Client(mcp) as client:
        args = {"task_id": "task", "destination_id": "section"}
        result = await client.call_tool("move-task", args)
        assert "Moved task to Prep. ID: `task`" in result.content[0].text
        result = await client.call_tool("move-task", args)
        assert "already at" in result.content[0].text
        records["project"]["status"] = "completed"
        result = await client.call_tool("move-task", args, raise_on_error=False)
        assert result.is_error
    assert send.call_count == 1


async def test_move_does_not_claim_success_when_things_ignores_destination(monkeypatch):
    from things_mcp.write_confirmation import observe

    monkeypatch.setattr("things_mcp.config.get_things_auth_token", lambda: "test-only")
    records = {
        "task": {"type": "to-do", "project": "still-in-project"},
        "area": {"type": "area", "title": "Home"},
    }
    monkeypatch.setattr(tools_planning.things, "get", records.get)
    monkeypatch.setattr(
        tools_planning, "observe", lambda read: observe(read, timeout=0)
    )
    send = Mock(return_value=True)
    monkeypatch.setattr(tools_planning, "execute_url", send)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "move-task",
            {"task_id": "task", "destination_id": "area"},
            raise_on_error=False,
        )
    assert result.is_error
    assert "destination was not confirmed" in result.content[0].text
    assert send.call_count == 1


async def test_capture_does_not_return_id_for_ambiguous_readback(monkeypatch):
    old = {"uuid": "pre-existing", "title": "Same"}
    monkeypatch.setattr(
        tools_tasks.things,
        "inbox",
        Mock(
            side_effect=[
                [old],
                [old, {"uuid": "a", "title": "Same"}, {"uuid": "b", "title": "Same"}],
            ]
        ),
    )
    send = Mock(return_value=True)
    monkeypatch.setattr(tools_tasks, "execute_url", send)
    async with Client(mcp) as client:
        result = await client.call_tool("capture-task", {"title": "Same"})
    assert "Creation was not confirmed" in result.content[0].text
    assert "ID:" not in result.content[0].text
    send.assert_called_once()


async def test_compact_reads_omit_content_and_detailed_reads_restore_it(monkeypatch):
    task = {
        "uuid": "task-id",
        "title": "File a form",
        "type": "to-do",
        "status": "incomplete",
        "start": "Inbox",
        "start_date": "2025-01-01",
        "deadline": "2025-01-02",
        "project_title": "Example project",
        "heading_title": "Prep",
        "heading": "heading-id",
        "area_title": "Example area",
        "notes": "Private clinical notes",
        "tags": ["Private personnel"],
        "checklist": 1,
    }
    checklist = Mock(
        return_value=[{"status": "incomplete", "title": "Private checklist step"}]
    )
    monkeypatch.setattr(tools_tasks.things, "inbox", lambda **kwargs: [task])
    monkeypatch.setattr(tools_tasks.things, "todos", lambda **kwargs: [task])
    monkeypatch.setattr(tools_tasks.things, "checklist_items", checklist)
    search = Mock(return_value=[task])
    monkeypatch.setattr(tools_utility.things, "search", search)

    private = [task["notes"], task["tags"][0], "Private checklist step"]
    async with Client(mcp) as client:
        for name, args in [
            ("get-tasks", {"view": "inbox", "context": task["tags"][0]}),
            ("search-tasks", {"query": task["notes"]}),
            ("focus-mode", {}),
            ("process-inbox", {}),
        ]:
            checklist.reset_mock()
            result = await client.call_tool(name, args)
            assert result.structured_content is None
            compact = result.content[0].text
            assert all(value not in compact for value in private)
            for value in (
                "task-id",
                "heading-id",
                "Prep",
                "Example project",
                "Example area",
                "2025-01-01",
                "2025-01-02",
                "incomplete",
                task["title"],
            ):
                assert value in compact
            checklist.assert_not_called()

            detailed = await client.call_tool(name, {**args, "include_details": True})
            assert detailed.structured_content is None
            assert all(value in detailed.content[0].text for value in private)
            checklist.assert_called_once_with("task-id")

    assert search.call_count == 2
    search.assert_called_with(task["notes"])
