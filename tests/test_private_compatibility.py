from base64 import urlsafe_b64encode
from hashlib import sha256
import re
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import fastmcp
import pytest
from fastmcp import Client
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.providers.github import GitHubTokenVerifier
from authlib.integrations.httpx_client import AsyncOAuth2Client
from starlette.testclient import TestClient

from things_mcp import tools_compatibility, tools_planning
from things_mcp.fast_server import _server_with_tools, mcp
from things_mcp.oauth_transport import OwnerTokenVerifier, build_oauth_app
from things_mcp.settings import Settings, get_settings


async def test_schedule_verifies_requested_heading_and_maps_legacy_reminder(
    monkeypatch,
):
    project = {
        "uuid": "project",
        "title": "Project",
        "type": "project",
        "status": "incomplete",
    }
    heading = {"uuid": "heading", "title": "Next"}
    monkeypatch.setattr(tools_planning.things, "projects", lambda: [project])
    monkeypatch.setattr(tools_planning.things, "get", lambda _: project)
    monkeypatch.setattr(tools_planning.things, "tasks", lambda **_: [heading])
    monkeypatch.setattr(
        tools_planning.things,
        "todos",
        Mock(
            side_effect=[
                [],
                [
                    {
                        "uuid": "new",
                        "title": "Task",
                        "heading": "heading",
                    }
                ],
            ]
        ),
    )
    dispatch = Mock(return_value=True)
    monkeypatch.setattr(tools_planning, "execute_url", dispatch)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "schedule-task",
            {
                "title": "Task",
                "project": "Project",
                "heading": "Next",
                "reminder_at": "tomorrow@6pm",
            },
        )
    assert "ID: `new`" in result.content[0].text
    query = parse_qs(urlsplit(dispatch.call_args.args[0]).query)
    assert query["heading"] == ["Next"]
    assert query["when"] == ["tomorrow@18:00"]


async def test_cancel_uses_confirmed_readback_and_automation_defaults_off(monkeypatch):
    monkeypatch.setattr("things_mcp.config.get_things_auth_token", lambda: "test-only")
    monkeypatch.setattr(
        tools_compatibility.things,
        "get",
        Mock(
            side_effect=[
                {"uuid": "task", "type": "to-do", "status": "incomplete"},
                {"uuid": "task", "type": "to-do", "status": "canceled"},
            ]
        ),
    )
    dispatch = Mock(return_value=True)
    script = Mock()
    monkeypatch.setattr(tools_compatibility, "execute_url", dispatch)
    monkeypatch.setattr(tools_compatibility, "run_applescript", script)
    async with Client(mcp) as client:
        listed = {tool.name for tool in await client.list_tools()}
        assert {"trash-task", "create-area"}.isdisjoint(listed)
        result = await client.call_tool("cancel-task", {"task_id": "task"})
        assert "Task canceled" in result.content[0].text
        blocked = await client.call_tool(
            "trash-task", {"task_id": "task", "confirm": True}, raise_on_error=False
        )
        assert blocked.is_error
    assert parse_qs(urlsplit(dispatch.call_args.args[0]).query)["canceled"] == ["true"]
    script.assert_not_called()


@pytest.fixture
def oauth_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(fastmcp.settings, "home", tmp_path)
    monkeypatch.setenv("THINGS_MCP_OAUTH_ALLOW_WRITES", "false")
    get_settings.cache_clear()
    yield Settings(
        things_mcp_oauth_url="https://things.example",
        things_mcp_oauth_github_client_id="test-client",
        things_mcp_oauth_github_client_secret="test-secret",
        things_mcp_oauth_github_user_id=123,
        things_mcp_oauth_redirect_uris="https://agent.example/callback",
    )
    get_settings.cache_clear()


def test_oauth_requires_auth_and_only_registers_approved_callbacks(oauth_settings):
    app = build_oauth_app(oauth_settings, _server_with_tools)
    with TestClient(app, base_url="https://things.example") as client:
        response = client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        )
        assert response.status_code == 401
        assert "resource_metadata" in response.headers["www-authenticate"]
        metadata = client.get("/.well-known/oauth-protected-resource/mcp").json()
        assert metadata["resource"] == "https://things.example/mcp"
        for uri, expected in [
            ("https://unapproved.example/callback", 400),
            ("https://agent.example/callback", 201),
        ]:
            result = client.post(
                "/register",
                json={"redirect_uris": [uri], "token_endpoint_auth_method": "none"},
            )
            assert result.status_code == expected, result.text


async def test_oauth_owner_validation_and_default_tool_visibility(
    monkeypatch, oauth_settings
):
    upstream = AsyncMock(
        return_value=AccessToken(
            token="provider-token",
            client_id="123",
            scopes=["read:user"],
            claims={"sub": "123"},
        )
    )
    monkeypatch.setattr(GitHubTokenVerifier, "verify_token", upstream)
    assert await OwnerTokenVerifier(123).verify_token("provider-token")
    assert await OwnerTokenVerifier(456).verify_token("provider-token") is None

    def factory(**kwargs):
        nonlocal server
        server = _server_with_tools(**kwargs)
        return server

    server = None
    build_oauth_app(oauth_settings, factory)
    async with Client(server) as client:
        listed = {tool.name for tool in await client.list_tools()}
        assert "things-health" in listed
        assert {
            "show-in-app",
            "cancel-task",
            "capture-tasks",
            "create-area",
        }.isdisjoint(listed)
        blocked = await client.call_tool(
            "capture-task", {"title": "Blocked"}, raise_on_error=False
        )
        assert blocked.is_error


def test_oauth_browser_approval_exchanges_for_a_separate_mcp_token(
    monkeypatch, oauth_settings
):
    exchange = AsyncMock(
        return_value={"access_token": "mock-upstream-token", "token_type": "bearer"}
    )
    monkeypatch.setattr(AsyncOAuth2Client, "fetch_token", exchange)
    upstream = AsyncMock(
        return_value=AccessToken(
            token="mock-upstream-token",
            client_id="123",
            scopes=["read:user"],
            claims={"sub": "123"},
        )
    )
    monkeypatch.setattr(GitHubTokenVerifier, "verify_token", upstream)

    resource = "https://things.example/mcp"
    callback = "https://agent.example/callback"
    verifier = "a" * 48
    challenge = (
        urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    with TestClient(
        build_oauth_app(oauth_settings, _server_with_tools),
        base_url="https://things.example",
        follow_redirects=False,
    ) as client:
        registration = client.post(
            "/register",
            json={"redirect_uris": [callback], "token_endpoint_auth_method": "none"},
        )
        assert registration.status_code == 201
        client_id = registration.json()["client_id"]
        auth = client.get(
            "/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": callback,
                "response_type": "code",
                "scope": "read:user",
                "state": "agent-state",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": resource,
            },
        )
        assert auth.status_code == 302, auth.text
        consent = client.get(auth.headers["location"])
        assert consent.status_code == 200
        fields = dict(
            re.findall(r'name="(txn_id|csrf_token)" value="([^"]+)"', consent.text)
        )
        login = client.post(
            "/consent",
            data={**fields, "action": "approve"},
            headers={"origin": "https://things.example"},
        )
        assert login.status_code == 302, login.text
        login_url = urlsplit(login.headers["location"])
        assert login_url.hostname == "github.com"
        state = parse_qs(login_url.query)["state"][0]
        approved = client.get(
            "/auth/callback", params={"code": "provider-code", "state": state}
        )
        assert approved.status_code == 302, approved.text
        redirect = urlsplit(approved.headers["location"])
        assert redirect.hostname == "agent.example"
        query = parse_qs(redirect.query)
        assert query["state"] == ["agent-state"]
        token = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": query["code"][0],
                "redirect_uri": callback,
                "code_verifier": verifier,
                "resource": resource,
            },
        )
        assert token.status_code == 200, token.text
        mcp_token = token.json()["access_token"]
        assert mcp_token != "mock-upstream-token"
        response = client.post(
            "/mcp",
            headers={
                "authorization": f"Bearer {mcp_token}",
                "accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert response.status_code == 200, response.text
