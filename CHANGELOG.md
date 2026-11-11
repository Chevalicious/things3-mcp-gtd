# Changelog

All notable changes to **things3-mcp-gtd** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - Unreleased

### Added

- Local stdio transport and a neutral `things3-mcp` command. The `things3-mcp-gtd` command still works.
- `THINGS_MCP_READ_ONLY` mode, which hides and blocks every tool that writes or opens Things.
- `move-task`: ID-based moves into areas, projects, and headings, with destination readback. Project listings can show heading IDs.
- `capture-tasks`: Inbox batches of up to 10 rows with per-row readback and no automatic replay.
- Item IDs and bounded database readback for captures, scheduled tasks, new projects, and completed tasks.
- Optional OAuth transport for remote MCP clients using the owner's GitHub login. It defaults to read-only.
- Compatibility tools for canceling tasks, filing tasks by name, and checking database access. Local area creation and Trash are opt-in.

### Changed

- Task lists and search return compact rows by default; pass `include_details` for notes, tags, checklists, and a local Things link.
- Creating missing tags is opt-in (`THINGS_MCP_ALLOW_TAG_CREATION`). Startup, reads, ordinary writes, and use of existing tags no longer use AppleScript or request Automation permission.
- Tool descriptions and server instructions no longer assume a workflow methodology. Tool names and arguments are unchanged.
- Setup documentation is client-agnostic and lives in the README.
- The default test suite no longer needs the Things app, and live-test cleanup only targets recorded IDs.

### Removed

- Legacy OAuth that exposed the Things URL token, and direct non-loopback HTTP binding. Local HTTP uses an optional separate bearer credential and validates Host and Origin.
- Client-specific integration guides, the LaunchAgent template, and the Smithery manifest.
- The generic `server` console command.
- Unused retry settings, the on-disk failed-operation queue, and the remote server icon.

### Fixed

- Combined search filters and project/area scheduling.
- Weekly reviews fetch project tasks in one query.

### Security

- Full Things URLs, which can contain the auth token and task text, are no longer logged.
- Writes are never retried after an uncertain handoff.

## [1.0.1] - 2026-05-10

### Changed

- Corrected README install paths and CLI command examples for pip-installed users
- Fixed documented tool count: 19 GTD-native tools (previously listed as 13)
- Added `things3-mcp-gtd` CLI entry point so `pip install` and `uvx` work as documented
- Removed AGENTS.md from public tracking (internal infrastructure notes)
- Removed dead code: disabled JSON API branch in url_scheme.py

## [1.0.0] - 2026-05-10

### Added

- **19 GTD-native MCP tools** organized by David Allen's five GTD stages:
  - **Capture:** `capture-task`
  - **Clarify:** `process-inbox`, `convert-to-project`
  - **Organize:** `schedule-task`, `delegate-task`, `defer-task`, `plan-project`, `modify-task`
  - **Reflect:** `daily-review`, `weekly-review`
  - **Engage:** `get-tasks`, `focus-mode`, `complete-task`
  - **Utility:** `search-tasks`, `get-projects`, `get-areas`, `get-tags`, `show-in-app`, `get-cache-stats`
- **FastMCP framework** — Modern async server with type-safe tool definitions
- **AppleScript bridge** — Fallback mechanism for reliable Things 3 access
- **Things URL scheme support** — Write operations via Things URL scheme
- **Streamable HTTP transport** — Single endpoint at `/mcp` for all clients
- **Caching layer** — TTL-based caching for read operations with auto-invalidation
- **Circuit breaker** — Prevents cascading failures on Things 3 unavailability
- **Rate limiting** — Prevents overwhelming Things 3 with rapid requests
- **Bidirectional auth** — Optional bearer token enforcement for `/mcp` endpoint
- **Auto-tag creation** — Missing tags are created automatically when used
- **Rich logging** — Structured JSON logging with debug/trace support
- **Shutdown summary** — Session statistics on graceful shutdown
- **Client compatibility** — Automatic schema transforms for n8n, ChatGPT, etc.

### Infrastructure

- **PyPI package:** `things3-mcp-gtd` — installable via `pip` or `uvx`
- **GitHub Actions:** Automated publishing via Trusted Publishing (OpenID Connect)
- **Test suite:** 144+ tests with both mocked unit tests and real integration tests
- **Documentation:** Developer guide, integration guides, privacy notice, terms of use

### Credits

Based on the original [things-mcp](https://github.com/hald/things-mcp) by Harald Lindstrøm.
Built with [FastMCP](https://gofastmcp.com) by Jonathan Lowin.
GTD methodology by David Allen.

[2.0.0]: https://github.com/Chevalicious/things3-mcp-gtd/releases/tag/v2.0.0
[1.0.1]: https://github.com/Chevalicious/things3-mcp-gtd/releases/tag/v1.0.1
[1.0.0]: https://github.com/Chevalicious/things3-mcp-gtd/releases/tag/v1.0.0
