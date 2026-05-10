# Agent Access — Things MCP Server

This guide covers an **optional** deployment pattern: running the server as a
persistent macOS LaunchAgent and exposing it to remote MCP clients (Claude
mobile, ChatGPT, etc.) through an `ngrok` tunnel. For a simple local-only
setup, see the **Quick Start** section of the project [README](../README.md).

> ## Read this first
>
> Once the LaunchAgent is installed, **do not also start the server manually**
> (e.g. `uv run server`). A second instance will collide with the LaunchAgent
> on port 8009 and produce a crash-restart loop. Use
> `launchctl kickstart -k gui/$(id -u)/com.things-mcp-server` to restart the
> server through the LaunchAgent instead.
>
> If the endpoint is unreachable, run `bash scripts/health-check.sh` and
> consult [docs/runbook-recovery.md](runbook-recovery.md) before trying to
> "fix" the server.

## Architecture

```
Claude Desktop  ─┐
Claude Mobile   ─┤
Claude Code     ─┤
OpenClaw        ─┼─► ngrok tunnel ──► localhost:8009 ──► FastMCP ──► Things 3
ChatGPT         ─┤   (optional)        (LaunchAgent)
Cursor / others ─┘
```

> All remote agents connect through the public tunnel URL. **Don't** point
> agents at `http://localhost:8009` directly when the LaunchAgent owns that
> port — direct connections from a client running on the same Mac can spawn
> a second server, causing port conflicts and repeated macOS permission
> prompts for `uv`.

## One-time setup (macOS)

### 1. Install and configure the server

```bash
git clone https://github.com/Chevalicious/things3-mcp-gtd.git
cd things3-mcp-gtd
uv pip install -e .
python scripts/configure_token.py   # writes THINGS_AUTH_TOKEN to ~/.things-mcp/config.json
```

### 2. Install the LaunchAgent

```bash
cp deploy/launchagents/com.things-mcp-server.plist.example \
   ~/Library/LaunchAgents/com.things-mcp-server.plist
```

Edit the plist and replace:

- `YOUR_USERNAME` with your macOS short username
- `YOUR_THINGS_DATA_ID` with the 5-character suffix on your local Things data
  directory. Find yours with:

```bash
ls ~/Library/Group\ Containers/JLMPQHK86H.com.culturedcode.ThingsMac/
# Look for ThingsData-XXXXX -- that XXXXX is your value.
```

Then load the agent:

```bash
launchctl load ~/Library/LaunchAgents/com.things-mcp-server.plist
```

### 3. Grant Full Disk Access to `uv` (one-time, survives reboots)

LaunchAgent processes run in a restricted macOS context and cannot read
`~/Library/Group Containers/` (where Things 3 stores its database) without
explicit TCC permission. The `uv` binary is the direct child of `launchd` and
must be granted Full Disk Access so the permission propagates to the Python
subprocess it spawns.

**System Settings → Privacy & Security → Full Disk Access → click `+` →
navigate to `~/.local/bin/uv` → Open → toggle ON.**

Without this, all read tools (`get-tasks`, `daily-review`, etc.) will fail
with `unable to open database file`.

### 4. Set up ngrok (for remote agent access)

```bash
brew install ngrok
ngrok config add-authtoken <your-ngrok-token>
```

Add the tunnel to `~/Library/Application Support/ngrok/ngrok.yml`:

```yaml
version: "3"
agent:
  authtoken: <your-ngrok-token>
tunnels:
  things-mcp:
    addr: 8009
    proto: http
    host_header: localhost
    domain: <your-domain>.ngrok-free.dev   # free static domain from ngrok dashboard
```

For persistence across reboots, install ngrok as its own LaunchAgent:

```bash
# Create ~/Library/LaunchAgents/com.<your-label>.ngrok.plist with:
#   Label:               com.<your-label>.ngrok
#   ProgramArguments:    [/usr/local/bin/ngrok, start, --all]
#   EnvironmentVariables: HOME + PATH
#   RunAtLoad: true, KeepAlive: true, ThrottleInterval: 30
launchctl load ~/Library/LaunchAgents/com.<your-label>.ngrok.plist
```

Or start manually:

```bash
ngrok start --all --config ~/Library/Application\ Support/ngrok/ngrok.yml
```

## Connecting each client

### Claude Desktop (local)

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "things-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://<your-domain>.ngrok-free.dev/mcp",
        "--header",
        "ngrok-skip-browser-warning: true"
      ]
    }
  }
}
```

Restart Claude Desktop after editing this file.

### Claude Mobile

In the Claude mobile app → Settings → MCP Servers → Add Server:

```
URL: https://<your-domain>.ngrok-free.dev/mcp
```

Note: the full `/mcp` path is required. The base domain alone returns 404.

### Claude Code (claude.ai/code)

claude.ai → Settings → Integrations → MCP Servers:

```
URL:    https://<your-domain>.ngrok-free.dev/mcp
Header: ngrok-skip-browser-warning: true
```

### OpenClaw

Use the ngrok URL (same as all other agents):

```json
{
  "things": {
    "transport": "streamable-http",
    "url": "https://<your-domain>.ngrok-free.dev/mcp",
    "headers": {
      "ngrok-skip-browser-warning": "true"
    }
  }
}
```

### Cursor / other remote agents

Use the ngrok HTTPS URL:

```
https://<your-domain>.ngrok-free.dev/mcp
```

If the agent sends a Bearer token, set `THINGS_MCP_REQUIRE_AUTH=true` in
`.env` and use the same value in `THINGS_AUTH_TOKEN`.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `THINGS_MCP_HOST` | `localhost` | Bind address |
| `THINGS_MCP_PORT` | `8009` | Port |
| `THINGS_AUTH_TOKEN` | — | **Required** for write operations |
| `THINGSDB` | (auto-detected) | Explicit path to `main.sqlite`; set in the LaunchAgent plist to skip the startup glob |
| `THINGS_MCP_REQUIRE_AUTH` | `false` | Enforce Bearer token on all `/mcp` requests |
| `THINGS_MCP_DEBUG` | `false` | Verbose console logging |
| `THINGS_MCP_NGROK_DOMAIN` | (unset) | Used by `scripts/health-check.sh` to verify the tunnel; safe to leave unset |

## Health check

```bash
bash scripts/health-check.sh
```

Verifies: LaunchAgent running, local port responding, optional ngrok tunnel
reachable, Things database file present, Things 3 process running.

To include the tunnel check, set `THINGS_MCP_NGROK_DOMAIN`:

```bash
THINGS_MCP_NGROK_DOMAIN=<your-domain>.ngrok-free.dev bash scripts/health-check.sh
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `unable to open database file` | `uv` missing Full Disk Access | Re-add `~/.local/bin/uv` to FDA in System Settings → Privacy & Security → Full Disk Access |
| Server hangs at startup, no port binding | Automation permission pending | System Settings → Privacy & Security → Automation → enable Things 3 for `uv`. Required once; the server blocks on AppleScript startup until granted. |
| Tools listed but all fail | Same as above, or Things 3 not open | Grant FDA + Automation; open Things 3 |
| 404 on ngrok URL | Missing `/mcp` path | Use the full URL: `https://<your-domain>.ngrok-free.dev/mcp` |
| Tunnel unreachable | ngrok not running | `launchctl kickstart -k gui/$(id -u)/com.<your-label>.ngrok` |
| Server not responding on port 8009 | LaunchAgent stopped | `launchctl kickstart -k gui/$(id -u)/com.things-mcp-server` |
| Repeated "uv would like to access data" prompts | Port 8009 conflict from a duplicate server instance | `lsof -ti:8009 \| xargs kill -9`, ensure no agent connects directly to localhost:8009 while the LaunchAgent is loaded |

## Log locations

```
~/.things-mcp-server.log   # stdout (session/request activity)
~/.things-mcp-server.err   # stderr (errors, stack traces)
~/.ngrok.log               # ngrok tunnel activity (if you log there)
```
