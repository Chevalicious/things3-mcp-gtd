"""Pytest configuration and shared fixtures for Things MCP tests."""

import pytest
import unittest.mock as mock
from typing import List, Dict, Any, Optional
import time
import uuid
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import settings first - pydantic-settings automatically loads .env
# This ensures THINGS_AUTH_TOKEN is available for all modules
from things_mcp.settings import get_settings

get_settings()  # Trigger settings load

import mcp.types as types  # noqa: E402 - must load after settings


# ============================================================================
# Pytest Plugins
# ============================================================================

pytest_plugins = ["tests.pytest_test_results"]

# ============================================================================
# Mock Data Generators
# ============================================================================


def create_mock_todo(
    uuid_str: Optional[str] = None,
    title: str = "Test Todo",
    notes: Optional[str] = None,
    status: str = "open",
    tags: Optional[List[str]] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    project: Optional[str] = None,
    area: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a mock todo dictionary matching things-py format."""
    return {
        "uuid": uuid_str or f"test-todo-{uuid.uuid4().hex[:8]}",
        "type": "to-do",
        "title": title,
        "notes": notes or "",
        "status": status,
        "tags": tags or [],
        "when": when,
        "deadline": deadline,
        "project": project,
        "area": area,
        "start": when or "inbox",
        "start_date": when,
        "stop_date": None,
        "checklist": [],
    }


def create_mock_project(
    uuid_str: Optional[str] = None,
    title: str = "Test Project",
    notes: Optional[str] = None,
    status: str = "open",
    tags: Optional[List[str]] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    area: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a mock project dictionary matching things-py format."""
    return {
        "uuid": uuid_str or f"test-project-{uuid.uuid4().hex[:8]}",
        "type": "project",
        "title": title,
        "notes": notes or "",
        "status": status,
        "tags": tags or [],
        "when": when,
        "deadline": deadline,
        "area": area,
        "items": items or [],
    }


def create_mock_area(
    uuid_str: Optional[str] = None,
    title: str = "Test Area",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a mock area dictionary matching things-py format."""
    return {
        "uuid": uuid_str or f"test-area-{uuid.uuid4().hex[:8]}",
        "type": "area",
        "title": title,
        "notes": notes or "",
    }


def create_mock_tag(
    uuid_str: Optional[str] = None,
    title: str = "test-tag",
    shortcut: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a mock tag dictionary matching things-py format."""
    return {
        "uuid": uuid_str or f"test-tag-{uuid.uuid4().hex[:8]}",
        "type": "tag",
        "title": title,
        "shortcut": shortcut,
    }


# ============================================================================
# Unit Test Fixtures (Mocked)
# ============================================================================


@pytest.fixture
def mock_things(monkeypatch):
    """Mock the things-py library for unit tests."""
    mock_things_module = mock.MagicMock()

    # Mock common functions
    mock_things_module.inbox = mock.Mock(return_value=[])
    mock_things_module.today = mock.Mock(return_value=[])
    mock_things_module.upcoming = mock.Mock(return_value=[])
    mock_things_module.anytime = mock.Mock(return_value=[])
    mock_things_module.someday = mock.Mock(return_value=[])
    mock_things_module.trash = mock.Mock(return_value=[])
    mock_things_module.last = mock.Mock(return_value=[])
    mock_things_module.todos = mock.Mock(return_value=[])
    mock_things_module.projects = mock.Mock(return_value=[])
    mock_things_module.areas = mock.Mock(return_value=[])
    mock_things_module.tags = mock.Mock(return_value=[])
    mock_things_module.get = mock.Mock(return_value=None)
    mock_things_module.search = mock.Mock(return_value=[])

    # Patch the things module

    for module in ("tools_tasks", "tools_planning", "tools_reviews", "tools_utility"):
        monkeypatch.setattr(f"things_mcp.{module}.things", mock_things_module)
    monkeypatch.setattr("things_mcp.formatters.things", mock_things_module)

    return mock_things_module


@pytest.fixture
def mock_applescript(monkeypatch):
    """Mock AppleScript execution for unit tests."""
    mock_run_applescript = mock.Mock(return_value="test-todo-id-123")

    monkeypatch.setattr(
        "things_mcp.applescript_bridge.run_applescript", mock_run_applescript
    )

    return {"run_applescript": mock_run_applescript}


@pytest.fixture
def mock_url_scheme(monkeypatch):
    """Mock URL scheme execution for unit tests."""
    mock_execute_url = mock.Mock(return_value=True)

    monkeypatch.setattr("things_mcp.url_scheme.execute_url", mock_execute_url)

    return {"execute_url": mock_execute_url}


@pytest.fixture
def mock_utils(monkeypatch):
    """Mock utility functions for unit tests."""
    # Mock circuit_breaker (used by url_scheme.py)
    mock_circuit_breaker = mock.Mock()
    mock_circuit_breaker.allow_operation = mock.Mock(return_value=True)
    mock_circuit_breaker.record_success = mock.Mock()
    mock_circuit_breaker.record_failure = mock.Mock()

    # Mock rate_limiter (used by url_scheme.py)
    mock_rate_limiter = mock.Mock()
    mock_rate_limiter.wait_if_needed = mock.Mock()

    monkeypatch.setattr("things_mcp.url_scheme.circuit_breaker", mock_circuit_breaker)
    monkeypatch.setattr("things_mcp.url_scheme.rate_limiter", mock_rate_limiter)

    return {
        "circuit_breaker": mock_circuit_breaker,
        "rate_limiter": mock_rate_limiter,
    }


# ============================================================================
# Real Integration Test Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def things_available():
    """Live writes require a deliberate opt-in on a disposable Things profile."""
    import os
    import platform
    import things

    if os.environ.get("THINGS_MCP_LIVE_TESTS") != "1" or platform.system() != "Darwin":
        return False
    try:
        things.todos(count_only=True)
        return True
    except (OSError, ValueError):
        return False


@pytest.fixture(autouse=True)
def skip_real_tests_if_unavailable(request):
    if "real" in request.keywords and not request.getfixturevalue("things_available"):
        pytest.skip("Live Things tests require THINGS_MCP_LIVE_TESTS=1 and Things 3")


class TestDataTracker:
    """Track created test items for automatic cleanup."""

    def __init__(self):
        self.created_todos: List[str] = []
        self.created_projects: List[str] = []
        self.created_tags: List[str] = []

    def add_todo(self, todo_id: str):
        """Track a created todo."""
        self.created_todos.append(todo_id)

    def add_project(self, project_id: str):
        """Track a created project."""
        self.created_projects.append(project_id)

    def add_tag(self, tag_name: str):
        """Track a created tag."""
        if tag_name not in self.created_tags:
            self.created_tags.append(tag_name)

    def cleanup(self):
        """Clean up all tracked test items."""
        # Use run_applescript for proper execution (handles multi-line scripts correctly)
        from things_mcp.applescript_bridge import run_applescript

        # Delete todos
        for todo_id in self.created_todos:
            try:
                # Use AppleScript to delete the todo
                # Note: run_applescript handles multi-line scripts via stdin
                script = f"""tell application "Things3"
    try
        set theTodo to to do id "{todo_id}"
        delete theTodo
    end try
end tell"""
                result = run_applescript(script)
                if result is False:
                    # Log but don't fail - cleanup errors are non-critical
                    print(f"Warning: Failed to delete todo {todo_id}")
            except Exception as e:
                # Ignore cleanup errors - they're non-critical
                print(f"Warning: Exception during todo cleanup for {todo_id}: {e}")

        # Delete projects
        for project_id in self.created_projects:
            try:
                script = f"""tell application "Things3"
    try
        set theProject to project id "{project_id}"
        delete theProject
    end try
end tell"""
                result = run_applescript(script)
                if result is False:
                    print(f"Warning: Failed to delete project {project_id}")
            except Exception as e:
                print(
                    f"Warning: Exception during project cleanup for {project_id}: {e}"
                )

        # Clear tracked items
        self.created_todos.clear()
        self.created_projects.clear()
        self.created_tags.clear()


@pytest.fixture
def test_data_tracker():
    """Fixture to track test data for automatic cleanup in real integration tests."""
    tracker = TestDataTracker()
    yield tracker
    # Cleanup tracked items after test
    tracker.cleanup()


def generate_test_title(prefix: str = "MCP-TEST") -> str:
    """Generate a unique test title with timestamp."""
    timestamp = int(time.time())
    random_suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{timestamp}-{random_suffix}"


# ============================================================================
# MCP Integration Test Fixtures
# ============================================================================


# Test Utilities
# ============================================================================


def assert_text_content(
    response: List[Any], expected_text_contains: Optional[str] = None
):
    """Assert that response is a list of TextContent with expected content."""
    assert isinstance(response, list)
    assert len(response) > 0
    assert isinstance(response[0], types.TextContent)
    assert response[0].type == "text"

    if expected_text_contains:
        assert expected_text_contains in response[0].text


def assert_error_response(
    response: List[Any], expected_error_contains: Optional[str] = None
):
    """Assert that response indicates an error."""
    assert isinstance(response, list)
    assert len(response) > 0
    assert isinstance(response[0], types.TextContent)

    # Check if it's an error (starts with ⚠️ or contains "Error")
    error_indicators = ["⚠️", "Error", "error"]
    has_error = any(indicator in response[0].text for indicator in error_indicators)
    assert has_error, f"Expected error response but got: {response[0].text}"

    if expected_error_contains:
        assert expected_error_contains in response[0].text
