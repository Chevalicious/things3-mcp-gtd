# Things 3 GTD MCP Server

A **Model Context Protocol (MCP) server** for [Things 3](https://culturedcode.com/things/) that brings Getting Things Done (GTD) methodology to AI assistants. macOS only.

[![PyPI](https://img.shields.io/pypi/v/things3-mcp-gtd)](https://pypi.org/project/things3-mcp-gtd/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What it is

This server exposes Things 3 to AI assistants (Claude Desktop, Claude Code, Claude Mobile, ChatGPT, n8n, Cursor, OpenClaw) over MCP. The tools are organized around David Allen's five GTD stages — **Capture, Clarify, Organize, Reflect, Engage** — so an assistant can help you *practice GTD*, not just CRUD a task database.

The shift from "database wrapper" to "GTD assistant" reflects a key insight about MCP design: **tools should match how agents think about problems**, not how the underlying APIs are structured.

## Requirements

| Requirement | Notes |
|---|---|
| **macOS** | Required. The server uses AppleScript and the Things URL scheme — neither work in Linux containers. |
| **Things 3** | Installed, with scripting permissions enabled. |
| **Python 3.12+** | Modern type hints and f-strings. |
| **uv** | Recommended package manager. `pip` works too. |

## Installation

```bash
pip install things3-mcp-gtd
# or, no install:
uvx things3-mcp-gtd
```

For a local development install, see [docs/DEVELOPERS.md](docs/DEVELOPERS.md).

> Review the [Privacy Notice](PRIVACY.md) and [Terms of Use](TERMS_OF_USE.md) before running the server.

## Configuration

Copy [`.env.example`](.env.example) to `.env` and set at minimum:

```bash
THINGS_AUTH_TOKEN=<paste from Things -> Settings -> General -> Enable Things URLs>
```

The server reads from environment variables and the `.env` file via `pydantic-settings`. All other settings (host, port, debug, auth enforcement) have sensible defaults — see `.env.example` for the full list.

Alternatively, run the interactive helper:

```bash
python scripts/configure_token.py
```

which writes the token to `~/.things-mcp/config.json`.

## Quick start

```bash
# 1. Make sure Things 3 is open
# 2. Start the server
uv run server
```

Verify it's reachable:

```bash
bash scripts/health-check.sh
```

The server binds to `localhost:8009` by default and exposes a single MCP endpoint at `/mcp` over streamable HTTP.

## Connecting an MCP client

### Claude Desktop (stdio)

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "things": {
      "command": "uv",
      "args": ["run", "server"]
    }
  }
}
```

### Claude Desktop / Claude Mobile / ChatGPT (remote HTTPS)

Front the server with an HTTPS tunnel (ngrok, Cloudflare Tunnel, etc.) and point your client at `https://<your-tunnel>/mcp`. Full walkthrough: [docs/agent-access.md](docs/agent-access.md).

### n8n / OpenClaw / Cursor

See the dedicated guides:

- [n8n](docs/integration-n8n.md)
- [ChatGPT](docs/integration-chatgpt.md)
- [OpenClaw (Clawdbot)](docs/integration-clawdbot.md)
- [Publishing / approval notes](docs/integration-approval.md)

Compatibility deep-dives: [n8n + FastMCP](docs/n8n-fastmcp-compatibility.md), [ChatGPT + FastMCP](docs/chatgpt-fastmcp-compatibility.md).

## Tools

13 tools organized by GTD stage:

### Capture

| Tool | Purpose |
|------|---------|
| `capture-task` | Quick-capture to Inbox without organizing. |

### Clarify

| Tool | Purpose |
|------|---------|
| `process-inbox` | Process the oldest inbox item with GTD decision guidance. |
| `convert-to-project` | Transform a task into a multi-step project. |

### Organize

| Tool | Purpose |
|------|---------|
| `schedule-task` | Create an organized task with context, dates, project, and tags. |
| `delegate-task` | Mark as Waiting For with a person and follow-up. |
| `defer-task` | Move to Someday/Maybe or schedule for a future date. |
| `plan-project` | Create a project with initial tasks atomically. |
| `modify-task` | Update an existing task or project. |

### Reflect

| Tool | Purpose |
|------|---------|
| `daily-review` | Today's tasks, overdue items, and inbox status. |
| `weekly-review` | Stalled projects, waiting-for items, someday review. |

### Engage

| Tool | Purpose |
|------|---------|
| `get-tasks` | Context-first task retrieval (replaces every per-list view tool). |
| `focus-mode` | Single most important task for the current context. |
| `complete-task` | Mark done by ID or fuzzy title match. |

### Utility

| Tool | Purpose |
|------|---------|
| `search-tasks` | Full-text and filtered search. |

> **Migration note (v1.x → v2.0):** 18 legacy CRUD-style tools (`get-inbox`, `add-todo`, `update-project`, etc.) were removed in favor of the GTD-native tools above. See [CHANGELOG.md](CHANGELOG.md) for the full mapping.

### GTD context tags

For best results, use consistent GTD tags in Things 3:

```
Contexts:  @computer, @phone, @office, @home, @errands, @anywhere
Energy:    high-energy, low-energy
Time:      5min, 15min, 30min, 1hr+
Status:    waiting-for
People:    @person-name (for agenda items)
```

## Optional: 24/7 remote access

If you want the server reachable from Claude Mobile, ChatGPT, or any agent off your Mac, run it as a macOS LaunchAgent fronted by an HTTPS tunnel. End-to-end walkthrough: [docs/agent-access.md](docs/agent-access.md). Recovery procedures for the most common operational issue (a hung Apple Event subsystem): [docs/runbook-recovery.md](docs/runbook-recovery.md).

## Development

For setup, architecture, testing, and contributing guidelines, see [docs/DEVELOPERS.md](docs/DEVELOPERS.md).

```bash
# CI-safe tests (no Things 3 required)
uv run python -m pytest tests

# Lint and format
uv run ruff check .
uv run ruff format .
```

This project uses [OpenSpec](openspec/project.md) for spec-driven development of significant changes.

## Future direction

This is an evolving experiment in GTD-native AI tooling. Potential directions:

- MCP **Resources** for ambient GTD state (inbox count, stalled projects)
- Smarter context detection based on time, location, and calendar
- Proactive GTD coaching during weekly reviews
- Multi-app GTD — extending the pattern beyond Things 3

Contributions and ideas welcome.

## Credits

- **[Jonathan Lowin](https://github.com/jlowin)** — [FastMCP](https://gofastmcp.com)
- **[things.py](https://github.com/thingsapi/things.py)** — Things 3 Python library
- **[David Allen](https://gettingthingsdone.com/)** — GTD methodology
- **[Cultured Code](https://culturedcode.com)** — Things 3

## License

MIT — see [LICENSE](LICENSE).

## Links

- [GitHub Issues](https://github.com/Chevalicious/things3-mcp-gtd/issues)
- [Changelog](CHANGELOG.md)
- [Things URL Scheme reference](https://culturedcode.com/things/support/articles/2803573/)
- [GTD methodology](https://gettingthingsdone.com/)
