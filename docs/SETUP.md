# Connect Things to your AI app

[← Overview](../README.md) · [Use an agent instead](../SETUP-AGENT.md)

## 1. Check what you have

- A Mac with Things 3 installed and opened under your user account.
- An AI app supporting **local MCP / stdio**. Stdio means the app starts and talks to the tool directly.
- [uv](https://docs.astral.sh/uv/getting-started/installation/), the installer used below.

Already running Things MCP? Use the agent guide to review your setup first. Preserve its environment and avoid starting a duplicate service.

## 2. Install Things 3 MCP

Open **Terminal**. Run:

```sh
uv tool install --python 3.13 'things3-mcp-gtd==2.0.0'
```

This installs version 2.0.0. If an installation already exists, review it before replacing anything.

Find the installed command:

```sh
command -v things3-mcp
```

If no path appears, use `uv tool dir --bin` and look for `things3-mcp` in that directory. Use its full absolute path below.

## 3. Add it to your AI app

Open your app's MCP settings and choose a **local / stdio** server.

| Field | Value |
| --- | --- |
| Name | `things` |
| Command | Full executable path from step 2 |
| Arguments | `--transport`, `stdio` |
| Environment variable | `THINGS_MCP_READ_ONLY` = `true` |

For apps accepting `mcpServers` JSON, merge this entry into existing settings. Replace the command path and preserve other servers:

```json
{
  "mcpServers": {
    "things": {
      "command": "/absolute/path/to/things3-mcp",
      "args": ["--transport", "stdio"],
      "env": { "THINGS_MCP_READ_ONLY": "true" }
    }
  }
}
```

Apps use different formats. If yours doesn't accept this, follow its current local MCP instructions or use the agent guide. Save and reload the connection or restart the app.

## 4. Try a read

Ask your AI:

> Use Things to show me today's tasks. Don't change anything.

The agent can call `get-cache-stats` to check the connection, then `get-tasks` with `{"view":"today"}` to check Things access. An empty task list is valid.

If macOS asks for access to Things' app container, allow the app that launches the server. If reads fail after denial, check that app in **System Settings → Privacy & Security**. Reading doesn't require a Things URL token, Accessibility access, or AppleScript Automation permission.

## Optional: enable writes

Continue when reads work and you want your AI to change Things.

1. In **Things → Settings → General**, turn on **Enable Things URLs**.
2. Remove `THINGS_MCP_READ_ONLY` from the server's environment and reload. Creating tasks and projects is now enabled.
3. For changes to existing tasks, click **Manage** beside Enable Things URLs. Copy the token directly into private local MCP settings as `THINGS_AUTH_TOKEN`, then reload. Don't paste it into chat.

Return to read-only by setting `THINGS_MCP_READ_ONLY=true` and reloading. Review your AI app's tool approval controls. You don't need to create a task to finish setup.

Creating missing tags, creating areas, and moving tasks to Trash have separate opt-ins that may require Automation permission. [Settings reference](REFERENCE.md#settings)

## Troubleshooting

| What you see | What to check |
| --- | --- |
| `uv: command not found` | Follow the uv installation link, then reopen Terminal. |
| Package download fails | Check your internet connection and that version 2.0.0 is available on PyPI. |
| Tool already installed | Review its version, clients, and services before replacing it. |
| App can't find the command | Use the full executable path. |
| Connection works but tasks fail | Check the launching app's macOS access to the Things container. |
| No tools appear | Confirm local MCP support, save settings, and reload the app. |
| Empty task list | Check the selected list in Things; an empty list isn't a connection failure. |
| No write tools | Expected with read-only enabled. |
| Write submitted but unconfirmed | Check Things before retrying. Never automatically replay an uncertain batch. |
| Existing remote service unreachable | Report the error to its owner; don't start or restart a duplicate server. |

For a bug report, include app name, macOS version, server version, and a redacted error. Exclude credentials, task content, and private configuration.
