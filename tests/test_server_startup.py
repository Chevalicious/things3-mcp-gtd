"""Run the installed module over a real stdio subprocess."""

import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_stdio_protocol_and_read_only_mode(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "things_mcp.things_fast_server", "--transport", "stdio"],
        env={**os.environ, "THINGS_MCP_READ_ONLY": "true"},
        cwd=tmp_path,
    )
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        listed = {tool.name for tool in (await session.list_tools()).tools}
        assert "get-tasks" in listed
        assert "capture-task" not in listed
        assert "capture-tasks" not in listed
        assert "move-task" not in listed
        assert "show-in-app" not in listed
        assert not (await session.call_tool("get-cache-stats", {})).isError
        assert (await session.call_tool("capture-task", {"title": "Blocked"})).isError
        blocked = await session.call_tool(
            "capture-tasks", {"tasks": [{"title": "Blocked"}]}
        )
        assert (
            blocked.isError and "disabled in read-only mode" in blocked.content[0].text
        )
        assert (
            await session.call_tool(
                "move-task", {"task_id": "task", "destination_id": "area"}
            )
        ).isError
