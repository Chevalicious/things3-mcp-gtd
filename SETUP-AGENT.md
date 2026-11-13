# Agent-assisted setup

Connect Things 3 to the user's chosen AI app on their Mac. Explain user actions in plain language. Finish with a verified read.

## Release target

Install the released `things3-mcp-gtd==2.0.0` package from PyPI. The executable is `things3-mcp`; Python 3.12 or newer is required. Source and documentation: https://github.com/Chevalicious/things3-mcp-gtd/tree/v2.0.0. Do not silently substitute a different version or development branch.

## Inspect first

1. Ask which AI app to connect if unknown. Consult its current official local MCP instructions; don't invent a settings path or assume it accepts `mcpServers` JSON.
2. Confirm macOS, Things 3 installed and opened under the current account, and local installation access. A remote coding environment cannot configure the user's Mac without an authorized connection.
3. Check for an existing `things3-mcp` or `things3-mcp-gtd` executable, version, relevant client entry, and managed Things MCP service. Keep private settings and secrets out of output.
4. Preserve other MCP entries and environment variables. Back up configuration before editing. If a working installation exists, assess it before replacing anything.
5. Do not restart a LaunchAgent, replace a managed service's Python environment, change its endpoint, or start a duplicate HTTP server. Report an unreachable existing service without attempting repairs.

## Install and configure

For a new installation with uv available:

```sh
uv tool install --python 3.13 'things3-mcp-gtd==2.0.0'
```

If uv is missing, use its [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/). Don't use sudo or force-replace an existing tool. Resolve an installation conflict with the user before replacing their working environment.

Find the absolute executable path using `command -v things3-mcp`, or inspect `uv tool dir --bin` if it isn't on PATH. Verify the executable exists. Configure the chosen app's supported local stdio entry:

- Command: the absolute executable path.
- Arguments: `--transport`, `stdio`.
- Environment: `THINGS_MCP_READ_ONLY=true`.

See the [manual guide](docs/SETUP.md) for generic JSON. Merge only the intended entry. Preserve an existing entry named `things` and resolve any conflict. Let the client launch stdio. Do not add a tunnel, public listener, OAuth service, or background daemon for this local setup.

## Verify

1. Explain how to reload the connection in the chosen app.
2. Through that client, call `get-cache-stats`, then `get-tasks` with `{"view":"today"}`. An empty list is valid. Don't reproduce task content in setup logs or reports.
3. Explain any specific macOS access prompt. Let the user grant permissions; don't broaden permissions speculatively.
4. Do not create, edit, complete, delete, or open tasks during setup. Do not run repository tests against the user's Things database.
5. If you cannot exercise the intended client, report configuration as prepared and verification as pending. Give the user the read-only test prompt from the manual guide.

## Optional writes and handoff

Keep read-only enabled unless the user requests writes. Explain the [optional write steps](docs/SETUP.md#optional-enable-writes). The user enters the Things URL token directly into private local configuration; never put it in chat, logs, source control, or command arguments. Leave tag creation and Automation writes disabled unless requested separately.

Report the installed revision and executable path, app configured, whether connection and task reads were verified, read-only status, settings backup location, and any user click or restart still needed. Exclude credentials and task content.
