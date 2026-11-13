"""Exercise the real ASGI transport without a port or Things data."""

import json

import pytest
from starlette.testclient import TestClient

from things_mcp.fast_server import _create_combined_app, mcp
from things_mcp.settings import Settings

TOKEN = "test-only-http-credential-123456789"
ACCEPT = {"Accept": "application/json, text/event-stream"}


def client(**settings):
    from unittest.mock import patch

    with patch(
        "things_mcp.fast_server.get_settings",
        return_value=Settings(_env_file=None, **settings),
    ):
        app = _create_combined_app(mcp, "streamable-http")
    return TestClient(app, base_url="http://127.0.0.1:8009")


def post(http, method, params=None, headers=None, request_id=1):
    body = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        body["id"] = request_id
    if params is not None:
        body["params"] = params
    return http.post("/mcp", json=body, headers=ACCEPT | (headers or {}))


def payload(response):
    assert response.status_code == 200, response.text
    if response.headers["content-type"].startswith("application/json"):
        return response.json()
    for line in response.text.splitlines():
        if line.startswith("data: "):
            message = json.loads(line[6:])
            if "id" in message:
                return message
    pytest.fail("No JSON-RPC response in the event stream")


def initialize(http, headers=None):
    headers = dict(headers or {})
    response = post(
        http,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1"},
        },
        headers,
    )
    headers["MCP-Session-Id"] = response.headers["mcp-session-id"]
    headers["MCP-Protocol-Version"] = payload(response)["result"]["protocolVersion"]
    assert (
        post(
            http, "notifications/initialized", headers=headers, request_id=None
        ).status_code
        == 202
    )
    return headers


def test_full_authenticated_protocol():
    with client(things_mcp_http_token=TOKEN, things_mcp_require_auth=True) as http:
        assert post(http, "initialize").status_code == 401
        assert (
            post(
                http, "initialize", headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 401
        )
        headers = initialize(http, {"Authorization": f"Bearer {TOKEN}"})
        tools = payload(post(http, "tools/list", headers=headers))["result"]["tools"]
        assert {"get-cache-stats", "capture-task", "capture-tasks", "move-task"} <= {
            tool["name"] for tool in tools
        }
        result = payload(
            post(
                http,
                "tools/call",
                {
                    "name": "get-cache-stats",
                    "arguments": {"sessionId": "client-extra"},
                },
                headers,
            )
        )["result"]
        assert not result.get("isError")
        assert "Cache Statistics" in result["content"][0]["text"]
        assert http.post("/token", headers=headers).status_code == 404
        assert (
            http.get(
                "/.well-known/oauth-authorization-server", headers=headers
            ).status_code
            == 404
        )


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({"Host": "example.invalid:8009"}, 421),
        ({"Origin": "https://example.invalid"}, 403),
        ({"Origin": "null"}, 403),
    ],
)
def test_http_request_boundary(headers, status):
    with client() as http:
        assert post(http, "initialize", headers=headers).status_code == status


@pytest.mark.parametrize(
    "settings",
    [
        {"things_mcp_require_auth": True},
        {"things_mcp_http_token": "short"},
        {"things_mcp_http_token": TOKEN, "things_auth_token": TOKEN},
        {"things_mcp_host": "0.0.0.0"},
    ],
)
def test_invalid_http_configuration_fails_closed(settings):
    with pytest.raises(ValueError):
        client(**settings)


def test_client_schema_transforms_are_isolated():
    with client() as http:
        strict = initialize(http, {"User-Agent": "ChatGPT"})
        standard = initialize(http)
        for headers, expect_strict in [(strict, True), (standard, False)]:
            tools = payload(post(http, "tools/list", headers=headers))["result"][
                "tools"
            ]
            schema = next(t["inputSchema"] for t in tools if t["name"] == "get-tasks")
            assert (
                set(schema.get("required", [])) == set(schema["properties"])
            ) is expect_strict
            if expect_strict:
                assert schema.get("additionalProperties") is False
