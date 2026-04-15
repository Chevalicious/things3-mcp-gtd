# OpenClaw integration (Clawdbot)

**OpenClaw** (often referred to in docs as **Clawdbot**) is a self-hosted gateway that connects chat channels to AI agents. It can register **remote MCP servers** so embedded runtimes (for example Pi) use the same tool definitions without duplicating config.

Things MCP is a **normal FastMCP streamable HTTP** server on `http://127.0.0.1:8009/mcp`. OpenClaw stores MCP server definitions under `mcp.servers` in config.

> **Platform note:** Things MCP requires **macOS + Things 3** where the MCP process runs. OpenClaw itself may run on other platforms; only the Things bridge must be on a Mac.

## Official documentation

- [OpenClaw home](https://docs.clawd.bot/) — overview and install
- [`openclaw mcp` CLI](https://docs.openclaw.ai/cli/mcp.md) — MCP server registry (`list`, `set`, `unset`) and `openclaw mcp serve`
- [Gateway configuration](https://docs.openclaw.ai/gateway/configuration.md) — config file layout

## Register Things MCP for OpenClaw runtimes

OpenClaw’s `openclaw mcp set` command stores a JSON object per server name. For **streamable HTTP**, set `transport` to `"streamable-http"` and `url` to your MCP endpoint (see upstream docs for the exact schema).

Example (local Mac):

```bash
openclaw mcp set things-gtd '{
  "url": "http://127.0.0.1:8009/mcp",
  "transport": "streamable-http"
}'
```

If the gateway runs on another machine, replace the host with the Mac’s LAN IP or tunnel URL and ensure the port is reachable.

**Stdio alternative:** MCP clients that only support stdio can launch the server as a subprocess:

```json
{
  "command": "uv",
  "args": ["run", "server"]
}
```

Use the `cwd` of your cloned repo so `uv` resolves the project. Prefer streamable HTTP when the client supports it so you do not need to duplicate the Python environment inside OpenClaw.

## ClawdHub and skills

Skills and the ClawdHub registry are documented in OpenClaw’s tooling docs (for example [ClawdHub](https://docs.openclaw.ai/tools/clawhub.md) and [Creating skills](https://docs.openclaw.ai/tools/creating-skills.md)). Publishing a skill that wraps Things MCP is separate from registering the MCP URL in `openclaw mcp set`; follow OpenClaw’s skill bundle format (`SKILL.md` plus supporting files) when you publish.

To install a published skill, use the workflow from the same docs (CLI commands evolve; `npx clawdhub@latest --help` is the source of truth). Example pattern:

```bash
npx clawdhub@latest install <skill-name>
```

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| Connection errors from OpenClaw to the URL | Confirm `uv run server` is running, `THINGS_MCP_PORT` matches, and firewalls allow the path. |
| Tools not listed | Ensure `transport` is `streamable-http` (not default SSE) for this server. |
| Writes fail | Set `THINGS_AUTH_TOKEN` in the server environment on the Mac. |

## See also

- [n8n + FastMCP compatibility](n8n-fastmcp-compatibility.md) — schema and middleware behavior (same server)
- [ChatGPT + FastMCP compatibility](chatgpt-fastmcp-compatibility.md) — strict schema notes
