"""Tests for url_scheme module - URL construction and JSON API builders."""

import pytest
from unittest.mock import patch
from urllib.parse import unquote


pytestmark = [pytest.mark.unit]

# Patch target: construct_url does `from . import config` lazily,
# so we patch the config function it actually calls.
PATCH_AUTH = "things_mcp.config.get_things_auth_token"


def _parse_things_url(url: str) -> tuple[str, dict]:
    """Helper: parse a things:/// URL into (command, params)."""
    assert url.startswith("things:///")
    rest = url[len("things:///") :]
    if "?" in rest:
        command, query = rest.split("?", 1)
        params = {}
        for pair in query.split("&"):
            key, value = pair.split("=", 1)
            params[key] = unquote(value)
        return command, params
    return rest, {}


class TestConstructUrl:
    """Tests for construct_url()."""

    @patch(PATCH_AUTH, return_value="")
    def test_basic_command(self, _):
        """Simple command with no params produces correct URL."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("show", {"id": "abc"})
        command, params = _parse_things_url(url)

        assert command == "show"
        assert params["id"] == "abc"

    @patch(PATCH_AUTH, return_value="my-secret-token")
    def test_auth_token_included(self, _):
        """Only updates receive the Things token."""
        from things_mcp.url_scheme import construct_url

        assert "auth-token" not in construct_url("add", {"title": "Test"})
        url = construct_url("update", {"id": "abc", "title": "Test"})
        _, params = _parse_things_url(url)

        assert params["auth-token"] == "my-secret-token"

    @patch(PATCH_AUTH, return_value="")
    def test_none_params_excluded(self, _):
        """None values in params dict are excluded from URL."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("add", {"title": "Task", "notes": None})
        _, params = _parse_things_url(url)

        assert "title" in params
        assert "notes" not in params

    @patch(PATCH_AUTH, return_value="test-token")
    def test_boolean_params_lowercase(self, _):
        """Boolean values are converted to lowercase strings."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("update", {"id": "x", "completed": True})
        _, params = _parse_things_url(url)

        assert params["completed"] == "true"

    @patch(PATCH_AUTH, return_value="")
    def test_tags_comma_separated(self, _):
        """Tag lists are joined with commas."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("add", {"title": "T", "tags": ["work", "urgent"]})
        _, params = _parse_things_url(url)

        assert params["tags"] == "work,urgent"

    @patch(PATCH_AUTH, return_value="")
    def test_empty_tags_excluded(self, _):
        """Empty/whitespace-only tag list is excluded from params."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("add", {"title": "T", "tags": ["", "  "]})
        _, params = _parse_things_url(url)

        assert "tags" not in params

    @patch(PATCH_AUTH, return_value="")
    def test_spaces_encoded_as_percent20(self, _):
        """Spaces in values are URL-encoded as %20."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("add", {"title": "Buy groceries"})
        assert "Buy%20groceries" in url

    @patch(PATCH_AUTH, return_value="")
    def test_list_params_comma_joined(self, _):
        """Non-tag lists are comma-joined."""
        from things_mcp.url_scheme import construct_url

        url = construct_url("add", {"title": "T", "items": ["a", "b", "c"]})
        _, params = _parse_things_url(url)

        assert params["items"] == "a,b,c"


class TestAddTodo:
    """Tests for add_todo() URL builder."""

    @patch(PATCH_AUTH, return_value="")
    def test_minimal_todo(self, _):
        """Minimal todo with just a title."""
        from things_mcp.url_scheme import add_todo

        url = add_todo(title="Buy milk")
        command, params = _parse_things_url(url)

        assert command == "add"
        assert params["title"] == "Buy milk"

    @patch(PATCH_AUTH, return_value="")
    def test_todo_with_all_fields(self, _):
        """Todo with all optional fields populated."""
        from things_mcp.url_scheme import add_todo

        url = add_todo(
            title="Review PR",
            notes="Check the edge cases",
            when="today",
            deadline="2026-03-01",
            tags=["work", "code-review"],
            checklist_items=["Check tests", "Check types"],
            list_title="Work Project",
            heading="Sprint 42",
        )
        command, params = _parse_things_url(url)

        assert command == "add"
        assert params["title"] == "Review PR"
        assert params["notes"] == "Check the edge cases"
        assert params["when"] == "today"
        assert params["deadline"] == "2026-03-01"
        assert "work,code-review" in params["tags"]
        assert "Check tests" in params["checklist-items"]
        assert params["list"] == "Work Project"
        assert params["heading"] == "Sprint 42"

    @patch(PATCH_AUTH, return_value="")
    def test_checklist_items_newline_separated(self, _):
        """Checklist items are joined with newlines."""
        from things_mcp.url_scheme import add_todo

        url = add_todo(title="T", checklist_items=["Step 1", "Step 2", "Step 3"])
        _, params = _parse_things_url(url)

        assert params["checklist-items"] == "Step 1\nStep 2\nStep 3"


class TestAddProject:
    """Tests for add_project() URL builder."""

    @patch(PATCH_AUTH, return_value="")
    def test_minimal_project(self, _):
        from things_mcp.url_scheme import add_project

        url = add_project(title="New Feature")
        command, params = _parse_things_url(url)

        assert command == "add-project"
        assert params["title"] == "New Feature"

    @patch(PATCH_AUTH, return_value="")
    def test_project_with_todos(self, _):
        """Todos are newline-separated in to-dos param."""
        from things_mcp.url_scheme import add_project

        url = add_project(title="P", todos=["Task 1", "Task 2"])
        _, params = _parse_things_url(url)

        assert params["to-dos"] == "Task 1\nTask 2"


class TestUpdateTodo:
    """Tests for update_todo() URL builder."""

    @patch(PATCH_AUTH, return_value="test-token")
    def test_update_title(self, _):
        from things_mcp.url_scheme import update_todo

        url = update_todo(id="uuid-123", title="New Title")
        command, params = _parse_things_url(url)

        assert command == "update"
        assert params["id"] == "uuid-123"
        assert params["title"] == "New Title"

    @patch(PATCH_AUTH, return_value="test-token")
    def test_update_completed(self, _):
        from things_mcp.url_scheme import update_todo

        url = update_todo(id="uuid-123", completed=True)
        _, params = _parse_things_url(url)

        assert params["completed"] == "true"

    @patch(PATCH_AUTH, return_value="test-token")
    def test_update_append_notes(self, _):
        from things_mcp.url_scheme import update_todo

        url = update_todo(id="x", append_notes="Added later")
        _, params = _parse_things_url(url)

        assert params["append-notes"] == "Added later"

    @patch(PATCH_AUTH, return_value="test-token")
    def test_update_only_provided_fields(self, _):
        """Only explicitly provided fields appear in URL."""
        from things_mcp.url_scheme import update_todo

        url = update_todo(id="x", title="New")
        _, params = _parse_things_url(url)

        assert "notes" not in params
        assert "when" not in params
        assert "deadline" not in params


class TestUpdateProject:
    """Tests for update_project() URL builder."""

    @patch(PATCH_AUTH, return_value="test-token")
    def test_update_project_title(self, _):
        from things_mcp.url_scheme import update_project

        url = update_project(id="proj-1", title="Renamed")
        command, params = _parse_things_url(url)

        assert command == "update-project"
        assert params["title"] == "Renamed"

    @patch(PATCH_AUTH, return_value="test-token")
    def test_update_project_completed(self, _):
        from things_mcp.url_scheme import update_project

        url = update_project(id="proj-1", completed=True)
        _, params = _parse_things_url(url)

        assert params["completed"] == "true"


class TestShowAndSearch:
    """Tests for show() and search() URL builders."""

    @patch(PATCH_AUTH, return_value="")
    def test_show_by_id(self, _):
        from things_mcp.url_scheme import show

        url = show(id="item-uuid")
        command, params = _parse_things_url(url)

        assert command == "show"
        assert params["id"] == "item-uuid"

    @patch(PATCH_AUTH, return_value="")
    def test_search(self, _):
        from things_mcp.url_scheme import search

        url = search(query="meeting notes")
        command, params = _parse_things_url(url)

        assert command == "search"
        assert params["query"] == "meeting notes"


class TestBuildTodoObject:
    """Tests for build_todo_object() JSON API builder."""

    def test_minimal_todo_object(self):
        from things_mcp.url_scheme import build_todo_object

        obj = build_todo_object(title="Test")

        assert obj["type"] == "to-do"
        assert obj["attributes"]["title"] == "Test"

    def test_todo_object_all_fields(self):
        from things_mcp.url_scheme import build_todo_object

        obj = build_todo_object(
            title="Task",
            notes="Details",
            when="today",
            deadline="2026-04-01",
            tags=["a", "b"],
            list_id="proj-uuid",
            heading="Section",
            completed=True,
        )
        attrs = obj["attributes"]

        assert attrs["title"] == "Task"
        assert attrs["notes"] == "Details"
        assert attrs["when"] == "today"
        assert attrs["deadline"] == "2026-04-01"
        assert attrs["tags"] == ["a", "b"]
        assert attrs["list-id"] == "proj-uuid"
        assert attrs["heading"] == "Section"
        assert attrs["completed"] is True

    def test_todo_object_omits_none_fields(self):
        from things_mcp.url_scheme import build_todo_object

        obj = build_todo_object(title="Just title")
        attrs = obj["attributes"]

        assert "notes" not in attrs
        assert "when" not in attrs
        assert "tags" not in attrs


class TestBuildProjectObject:
    """Tests for build_project_object() JSON API builder."""

    def test_minimal_project_object(self):
        from things_mcp.url_scheme import build_project_object

        obj = build_project_object(title="My Project")

        assert obj["type"] == "project"
        assert obj["attributes"]["title"] == "My Project"

    def test_project_with_items(self):
        from things_mcp.url_scheme import build_project_object, build_todo_object

        items = [build_todo_object("Task 1"), build_todo_object("Task 2")]
        obj = build_project_object(title="P", items=items)

        assert len(obj["attributes"]["items"]) == 2


class TestBuildHeadingObject:
    """Tests for build_heading_object()."""

    def test_basic_heading(self):
        from things_mcp.url_scheme import build_heading_object

        obj = build_heading_object(title="Phase 1")

        assert obj["type"] == "heading"
        assert obj["attributes"]["title"] == "Phase 1"

    def test_archived_heading(self):
        from things_mcp.url_scheme import build_heading_object

        obj = build_heading_object(title="Old", archived=True)
        assert obj["attributes"]["archived"] is True


class TestBuildChecklistItem:
    """Tests for build_checklist_item()."""

    def test_basic_checklist_item(self):
        from things_mcp.url_scheme import build_checklist_item

        obj = build_checklist_item(title="Do thing")

        assert obj["type"] == "checklist-item"
        assert obj["attributes"]["title"] == "Do thing"

    def test_completed_checklist_item(self):
        from things_mcp.url_scheme import build_checklist_item

        obj = build_checklist_item(title="Done", completed=True)
        assert obj["attributes"]["completed"] is True


def test_unconfirmed_delivery_is_not_replayed_or_logged(monkeypatch, caplog):
    from subprocess import TimeoutExpired
    from unittest.mock import Mock

    from things_mcp import url_scheme

    monkeypatch.setattr(url_scheme.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(url_scheme, "circuit_breaker", Mock())
    monkeypatch.setattr(url_scheme, "rate_limiter", Mock())
    url = "things:///update?id=test&auth-token=synthetic-private-value"
    run = Mock(side_effect=TimeoutExpired(["open", url], 5))
    monkeypatch.setattr(url_scheme.subprocess, "run", run)
    with caplog.at_level("DEBUG"):
        assert not url_scheme.execute_url(url)
    assert run.call_count == 1
    assert "synthetic-private-value" not in caplog.text


def test_update_requires_things_token(monkeypatch):
    from fastmcp.exceptions import ToolError
    from things_mcp.url_scheme import update_todo

    monkeypatch.setattr(PATCH_AUTH, lambda: "")
    with pytest.raises(ToolError, match="THINGS_AUTH_TOKEN"):
        update_todo("task-id", completed=True)


def test_project_template_keeps_checklists_under_headings():
    import json

    from things_mcp.url_scheme import add_project_with_tasks

    _, params = _parse_things_url(
        add_project_with_tasks(
            "Project",
            [{"title": "Root"}],
            headings={
                "Prep": [{"title": "Grouped task", "checklist_items": ["First step"]}]
            },
        )
    )
    items = json.loads(params["data"])[0]["attributes"]["items"]
    assert [item["type"] for item in items] == ["to-do", "heading", "to-do"]
    assert items[2]["attributes"]["checklist-items"] == [
        {"type": "checklist-item", "attributes": {"title": "First step"}}
    ]
