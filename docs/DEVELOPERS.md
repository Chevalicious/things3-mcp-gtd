# Development

Run these commands from the repository root with [uv](https://docs.astral.sh/uv/):

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
```

The default suite exercises real stdio and in-process Streamable HTTP, using test data or mocks where tools would access Things. It requires no Things installation, AppleScript permissions, or open network port. See [live testing](TESTING.md).

The server entry point is `things_fast_server.py`; tool registration and HTTP checks are in `fast_server.py`. Tools are grouped by tasks, planning, reviews, and utilities. Keep established MCP tool names and argument types stable. `server_core.py` has compatibility transforms for older clients; keep them isolated between requests.

All task reads use `things-py` with SQLite in read-only mode. App writes go through `url_scheme.py`; tag creation goes through `tag_handler.py`. A successful URL handoff doesn't prove Things made a change. Verify side effects where a later write depends on them. Keep tokens, task content, and full command URLs out of logs and test reports.

Before a release, test the built wheel on macOS, verify a real read and a disposable write, and run the checks on the minimum Python version. Release automation is separate from local builds.
