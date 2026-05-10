# n8n integration

Connect the Things MCP server to n8n workflows using the **MCP Client Tool** node so AI Agent nodes can call GTD tools against your local Things 3 database.

## Prerequisites

- **n8n** with the LangChain cluster nodes (MCP Client Tool). Use a current release; HTTP streamable transport is the recommended path (see [n8n PR #15454](https://github.com/n8n-io/n8n/pull/15454)).
- **Things MCP** running where n8n can reach it (same machine, Docker host networking, or VPN).
- **macOS + Things 3** on the machine running the MCP server (this project does not run the Things integration on Linux).

## Official documentation

- [MCP Client Tool node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp) — n8n docs
- [MCP introduction](https://modelcontextprotocol.io/introduction) — protocol overview

## Server URL and transport

1. Start Things MCP (default: `localhost:8009`, transport `streamable-http`).
2. In the MCP Client Tool node, set the server URL to the **streamable HTTP** endpoint:

   `http://localhost:8009/mcp`

   If n8n runs in Docker and the server runs on the host, use `http://host.docker.internal:8009/mcp` (macOS/Windows) or your LAN address.

3. Choose **HTTP streaming / streamable HTTP** if the node offers a transport choice (SSE is deprecated in MCP; this server exposes streamable HTTP only).

## Workflow outline

1. Add an **AI Agent** (or compatible agent) node.
2. Connect **MCP Client Tool** as a sub-node / tool source for that agent.
3. Point it at `http://<host>:8009/mcp`.
4. Optionally restrict which tools are exposed (the server publishes GTD tools such as `capture-task`, `get-tasks`, etc.).

## Authentication

Things MCP does not add HTTP auth by default. If you expose it beyond localhost, put a reverse proxy or tunnel in front and use the MCP Client Tool’s **Bearer** or **generic header** options to match your proxy.

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| Validation errors mentioning extra fields | n8n may send `toolCallId`, `sessionId`, `action`, `chatInput`. This server strips them in middleware. Update to a current server release if errors persist. See [n8n#21500](https://github.com/n8n-io/n8n/issues/21500). |
| `anyOf` / schema errors in the node | Schemas are flattened for n8n compatibility. See [n8n + FastMCP compatibility](n8n-fastmcp-compatibility.md). |
| Connection refused | Confirm `uv run server` is running, port `THINGS_MCP_PORT` matches, and firewall allows the path from n8n to the host. |

## See also

- [n8n + FastMCP compatibility](n8n-fastmcp-compatibility.md) — technical quirks and mitigations
