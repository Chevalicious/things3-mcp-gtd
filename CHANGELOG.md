# Changelog

All notable changes to **things3-mcp-gtd** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.1]: https://github.com/Chevalicious/things3-mcp-gtd/releases/tag/v1.0.1
[1.0.0]: https://github.com/Chevalicious/things3-mcp-gtd/releases/tag/v1.0.0
