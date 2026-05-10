# Changelog

All notable changes to the **Things 3 GTD MCP Server** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-10

### BREAKING CHANGES

- **Removed 18 deprecated tool aliases** - Legacy CRUD-style tools removed in favor of GTD-native tools
  - **Migration guide:**

    | Removed Tool | Replacement |
    |--------------|-------------|
    | `get-inbox` | `get-tasks(list_filter="inbox")` |
    | `get-today` | `get-tasks(list_filter="today")` |
    | `get-upcoming` | `get-tasks(list_filter="upcoming")` |
    | `get-anytime` | `get-tasks(list_filter="anytime")` |
    | `get-someday` | `get-tasks(list_filter="someday")` |
    | `get-logbook` | `get-tasks(list_filter="logbook")` |
    | `get-trash` | `get-tasks(list_filter="trash")` |
    | `get-todos` | `get-tasks()` |
    | `get-tagged-items` | `get-tasks(tag="tag-name")` |
    | `get-recent` | `get-tasks(list_filter="logbook")` |
    | `search-todos` | `search-tasks` |
    | `search-advanced` | `search-tasks` |
    | `search-items` | `search-tasks` |
    | `add-todo` | `capture-task` or `schedule-task` |
    | `add-project` | `plan-project` |
    | `update-todo` | `modify-task` |
    | `update-project` | `modify-task` |
    | `show-item` | `show-in-app` |

- **Removed SSE transport support** - SSE transport is deprecated in MCP protocol (2025-03-26)
  - Removed `/sse/` endpoint - all clients now use `/mcp` (streamable-http transport)
  - Transport configuration simplified: `THINGS_MCP_TRANSPORT` now only accepts `"streamable-http"` (default)
  - **Migration**: Update `THINGS_MCP_TRANSPORT` from `"both"` or `"sse"` to `"streamable-http"` or remove it to use default
  - ChatGPT, Claude Desktop, and n8n all use streamable-http transport via `/mcp` endpoint

### Changed

- **Split server into GTD-aligned modules** - Major refactoring for maintainability:
  - `fast_server.py` reduced from 2,404 lines to 111 lines (entry point only)
  - New `server_core.py` - Server factory, n8n middleware, schema patches
  - New `tool_annotations.py` - Shared tool annotations dictionary
  - New `tools_gtd_core.py` - GTD Engage/Capture/Clarify tools (6 tools)
  - New `tools_gtd_organize.py` - GTD Organize stage tools (5 tools)
  - New `tools_gtd_reflect.py` - GTD Reflect stage tools (2 tools)
  - New `tools_utility.py` - Utility tools (6 tools)
  - Each module now has focused responsibility, easier to test and maintain

### Added

- **THINGS_MCP_DEBUG environment variable** - Enable verbose console logging for debugging
  - When `false` (default): Console shows INFO level only
  - When `true`: Console shows DEBUG level (verbose output)
  - File logs always capture DEBUG regardless of this setting

### Fixed

- **convert-to-project now preserves checklist items and deadline**
  - Checklist items from the original task are converted to project tasks
  - Task deadline is preserved on the project (not on child tasks)
  - Only incomplete checklist items are converted (completed items are skipped)

### Documentation

- **n8n compatibility documentation** - New `docs/n8n-fastmcp-compatibility.md` documenting:
  - Extra parameter stripping (toolCallId, sessionId, etc.)
  - anyOf schema flattening for n8n's MCP client
  - Null value handling in tool arguments
  - Recommendations for FastMCP team

### Previous Changes

- **Upgraded to FastMCP 3.0.0b1** - Major framework upgrade with new features:
  - All tool functions converted to `async def` for better performance
  - Added `Context` dependency injection for operation logging via `await ctx.info()`
  - Implemented tool timeouts: write operations (30s), read operations (5s)
  - New error handling pattern: `raise ToolError("message")` instead of returning error strings
  - Fixed deprecation warning for `datetime.utcnow()` → `datetime.now(datetime.UTC)`

### Fixed

- Fixed 39 ruff linting errors including unused imports, bare except clauses, and duplicate function definitions
- Applied consistent code formatting across 18 files
- Updated async test suite to properly await tool function calls


[1.0.0]: https://github.com/Chevalicious/things3-mcp-gtd/releases/tag/v1.0.0
