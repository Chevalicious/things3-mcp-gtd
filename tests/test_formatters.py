"""Tests for formatters module - output formatting for todos, projects, areas, tags."""

import pytest
from unittest.mock import patch


pytestmark = [pytest.mark.unit]


class TestFormatTodo:
    """Tests for format_todo()."""

    def test_minimal_todo(self):
        """Format a todo with only required fields."""
        from things_mcp.formatters import format_todo

        todo = {"title": "Buy milk", "uuid": "abc-123", "type": "to-do"}
        result = format_todo(todo, include_details=True)

        assert "Title: Buy milk" in result
        assert "UUID: abc-123" in result
        assert "Type: to-do" in result

    def test_todo_with_status(self):
        """Status field is included when present."""
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "status": "completed",
        }
        result = format_todo(todo, include_details=True)
        assert "Status: completed" in result

    def test_todo_without_status(self):
        """Status line is omitted when status is empty/None."""
        from things_mcp.formatters import format_todo

        todo = {"title": "Task", "uuid": "u1", "type": "to-do", "status": ""}
        result = format_todo(todo, include_details=True)
        assert "Status:" not in result

    def test_todo_with_dates(self):
        """Start date, deadline, and completion date are formatted."""
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "start_date": "2026-03-01",
            "deadline": "2026-03-15",
            "stop_date": "2026-03-10",
        }
        result = format_todo(todo, include_details=True)

        assert "Start Date: 2026-03-01" in result
        assert "Deadline: 2026-03-15" in result
        assert "Completed: 2026-03-10" in result

    def test_todo_without_dates(self):
        """Date lines are omitted when not present."""
        from things_mcp.formatters import format_todo

        todo = {"title": "Task", "uuid": "u1", "type": "to-do"}
        result = format_todo(todo, include_details=True)

        assert "Start Date:" not in result
        assert "Deadline:" not in result
        assert "Completed:" not in result

    def test_todo_with_notes(self):
        """Notes are included when present."""
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "notes": "Some important notes",
        }
        result = format_todo(todo, include_details=True)
        assert "Notes: Some important notes" in result

    def test_todo_with_start_list(self):
        """Start/list location is included."""
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "start": "today",
        }
        result = format_todo(todo, include_details=True)
        assert "List: today" in result

    def test_todo_with_tags(self):
        """Tags are comma-separated."""
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "tags": ["urgent", "work", "meeting"],
        }
        result = format_todo(todo, include_details=True)
        assert "Tags: urgent, work, meeting" in result

    def test_todo_with_empty_tags(self):
        """Empty tag list doesn't produce Tags line."""
        from things_mcp.formatters import format_todo

        todo = {"title": "Task", "uuid": "u1", "type": "to-do", "tags": []}
        result = format_todo(todo, include_details=True)
        assert "Tags:" not in result

    def test_todo_with_checklist(self):
        """Checklist items are rendered with status symbols."""
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "checklist": [
                {"title": "Step 1", "status": "completed"},
                {"title": "Step 2", "status": "open"},
            ],
        }
        result = format_todo(todo, include_details=True)

        assert "Checklist:" in result
        assert "\u2713 Step 1" in result
        assert "\u25a1 Step 2" in result

    def test_todo_with_empty_checklist(self):
        """Empty checklist list still produces header but no items."""
        from things_mcp.formatters import format_todo

        todo = {"title": "Task", "uuid": "u1", "type": "to-do", "checklist": []}
        result = format_todo(todo, include_details=True)
        # Code adds "Checklist:" header for any list (even empty)
        assert "Checklist:" in result
        # But no items follow
        lines = result.split("\n")
        checklist_idx = next(i for i, line in enumerate(lines) if "Checklist:" in line)
        # No more lines after the header (or none with checkbox symbols)
        remaining = lines[checklist_idx + 1 :]
        assert all("\u2713" not in line and "\u25a1" not in line for line in remaining)

    def test_todo_with_no_checklist_key(self):
        """Missing checklist key doesn't produce Checklist line."""
        from things_mcp.formatters import format_todo

        todo = {"title": "Task", "uuid": "u1", "type": "to-do"}
        result = format_todo(todo, include_details=True)
        assert "Checklist:" not in result

    def test_todo_uses_joined_destinations_without_lookups(self):
        from things_mcp.formatters import format_todo

        todo = {
            "title": "Task",
            "uuid": "u1",
            "type": "to-do",
            "project": "proj-id",
            "project_title": "My Project",
            "area": "area-id",
            "heading": "heading-id",
            "heading_title": "Prep",
        }
        with patch("things_mcp.formatters.things") as mock_things:
            result = format_todo(todo)

        assert "Project: My Project" in result
        assert "Area: area-id" in result
        assert "Heading: Prep (ID: heading-id)" in result
        mock_things.get.assert_not_called()


class TestFormatProject:
    """Tests for format_project()."""

    def test_minimal_project(self):
        """Format a project with only required fields."""
        from things_mcp.formatters import format_project

        project = {"title": "Website Redesign", "uuid": "proj-1"}
        with patch("things_mcp.formatters.things"):
            result = format_project(project)

        assert "Title: Website Redesign" in result
        assert "UUID: proj-1" in result

    def test_project_omits_notes(self):
        from things_mcp.formatters import format_project

        project = {"title": "Proj", "uuid": "p1", "notes": "Important project"}
        with patch("things_mcp.formatters.things"):
            result = format_project(project)

        assert "Important project" not in result

    def test_project_with_area(self):
        """Area is resolved for projects."""
        from things_mcp.formatters import format_project

        project = {
            "title": "Proj",
            "uuid": "p1",
            "area": "area-1",
            "area_title": "Work",
        }
        with patch("things_mcp.formatters.things") as mock_things:
            result = format_project(project)

        assert "Area: Work" in result
        mock_things.get.assert_not_called()

    def test_project_include_items(self):
        """include_items=True lists todo titles."""
        from things_mcp.formatters import format_project

        project = {"title": "Proj", "uuid": "p1"}
        with patch("things_mcp.formatters.things") as mock_things:
            mock_things.tasks.return_value = [
                {"title": "Prep", "uuid": "heading-1", "type": "heading"},
                {"title": "Task A", "type": "to-do"},
                {"title": "Task B", "type": "to-do"},
            ]
            result = format_project(project, include_items=True)

        assert "Tasks:" in result
        assert "- Task A" in result
        assert "- Task B" in result
        assert "Prep (ID: `heading-1`)" in result

    def test_project_include_items_empty(self):
        """No Tasks section when project has no todos."""
        from things_mcp.formatters import format_project

        project = {"title": "Proj", "uuid": "p1"}
        with patch("things_mcp.formatters.things") as mock_things:
            mock_things.tasks.return_value = []
            result = format_project(project, include_items=True)

        assert "Tasks:" not in result


class TestFormatArea:
    """Tests for format_area()."""

    def test_minimal_area(self):
        """Format an area with only required fields."""
        from things_mcp.formatters import format_area

        area = {"title": "Personal", "uuid": "area-1"}
        with patch("things_mcp.formatters.things"):
            result = format_area(area)

        assert "Title: Personal" in result
        assert "UUID: area-1" in result

    def test_area_omits_notes(self):
        from things_mcp.formatters import format_area

        area = {"title": "Work", "uuid": "a1", "notes": "All work stuff"}
        with patch("things_mcp.formatters.things"):
            result = format_area(area)

        assert "All work stuff" not in result

    def test_area_include_items(self):
        """include_items lists both projects and todos."""
        from things_mcp.formatters import format_area

        area = {"title": "Work", "uuid": "a1"}
        with patch("things_mcp.formatters.things") as mock_things:
            mock_things.projects.return_value = [{"title": "Project X"}]
            mock_things.todos.return_value = [{"title": "Loose task"}]
            result = format_area(area, include_items=True)

        assert "Projects:" in result
        assert "- Project X" in result
        assert "Tasks:" in result
        assert "- Loose task" in result


class TestFormatTag:
    """Tests for format_tag()."""

    def test_minimal_tag(self):
        from things_mcp.formatters import format_tag

        tag = {"title": "urgent", "uuid": "tag-1"}
        with patch("things_mcp.formatters.things"):
            result = format_tag(tag)

        assert "Title: urgent" in result
        assert "UUID: tag-1" in result

    def test_tag_with_shortcut(self):
        from things_mcp.formatters import format_tag

        tag = {"title": "urgent", "uuid": "tag-1", "shortcut": "u"}
        with patch("things_mcp.formatters.things"):
            result = format_tag(tag)

        assert "Shortcut: u" in result

    def test_tag_include_items(self):
        from things_mcp.formatters import format_tag

        tag = {"title": "urgent", "uuid": "tag-1"}
        with patch("things_mcp.formatters.things") as mock_things:
            mock_things.todos.return_value = [{"title": "Fix bug"}]
            result = format_tag(tag, include_items=True)

        assert "Tagged Items:" in result
        assert "- Fix bug" in result
