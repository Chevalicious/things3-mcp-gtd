# Notes for AI coding agents

This file is a short orientation for AI coding assistants working on this
repository. Human contributors should read [`README.md`](README.md) and
[`docs/DEVELOPERS.md`](docs/DEVELOPERS.md) instead.

## Don't start the MCP server yourself

If you're running on a machine where the Things MCP server is managed by a
macOS LaunchAgent, **do not** run `uv run server`, `python -m things_mcp`,
or any other command that binds port 8009. A second instance will collide
with the LaunchAgent and trigger a crash-restart loop with repeated macOS
permission dialogs.

If the MCP endpoint is unreachable, *report it* — don't try to fix it.
Diagnose with `bash scripts/health-check.sh` and consult
[`docs/runbook-recovery.md`](docs/runbook-recovery.md).

## Repo conventions

- Lint and format with `ruff check .` and `ruff format .` before committing.
- CI-safe tests: `uv run python -m pytest tests`. Tests marked `real`
  require Things 3 and run only on macOS dev machines.
- Significant architectural changes should be proposed under
  `openspec/changes/<change-id>/` (see `openspec/project.md`).
- Never log task titles or notes — they're user PII.
  Use the redaction helpers in `src/things_mcp/logging_config.py`.

## Recovery runbook

Apple Event hangs and LaunchAgent recovery procedures live in
[`docs/runbook-recovery.md`](docs/runbook-recovery.md).
