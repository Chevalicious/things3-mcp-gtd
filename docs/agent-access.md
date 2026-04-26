# Agent Access — Things MCP Server

How to connect AI agents and remote clients to the Things MCP server running as a macOS LaunchAgent.

## Architecture

```
Claude Desktop  ──mcp-remote──┐
Claude Mobile   ──HTTPS───────┤
OpenClaw agents ──HTTP────────┼──► ngrok tunnel ──► localhost:8009 ──► FastMCP server ──► Things 3
Hermes agents   ──HTTPS───────┤                       (LaunchAgent)       (things-py)
Cursor          ──HTTPS───────┘

OpenClaw (local machine) ──► http://127.0.0.1:8009/mcp  (direct, no tunnel)
```

## One-Time macOS Setup

### 1. Install and configure the server

```bash
git clone https://github.com/CaseyRo/mcp-things.git
cd mcp-things
uv pip install -e .
python scripts/configure_token.py   # sets THINGS_AUTH_TOKEN in .env
```

### 2. Install the LaunchAgent

Copy the plist from this repo and install it:

```bash
cp deploy/launchagents/com.nicoloorozco.things-mcp-server.plist \
   ~/Library/LaunchAgents/com.nicoloorozco.things-mcp-server.plist
```

Edit the plist to replace `nicoloorozco` with your username and update the `THINGSDB` path to match your Things database location (the `ThingsData-ZHBUE` segment differs per account):

```bash
# Find your actual database path:
ls ~/Library/Group\ Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things\ Database.thingsdatabase/main.sqlite
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.nicoloorozco.things-mcp-server.plist
```

### 3. Grant Full Disk Access to `uv` (one-time, survives reboots)

LaunchAgent processes run in a restricted macOS context and cannot read `~/Library/Group Containers/` (where Things 3 stores its database) without explicit TCC permission. The `uv` binary is the direct child of launchd and must be granted Full Disk Access so the permission propagates to the Python subprocess it spawns.

**System Settings → Privacy & Security → Full Disk Access → click `+` → navigate to `~/.local/bin/uv` → Open → toggle ON**

Without this, all read tools (`get-tasks`, `daily-review`, etc.) will fail with `unable to open database file`.

### 4. Set up ngrok (for remote agent access)

```bash
# Install ngrok
brew install ngrok

# Authenticate
ngrok config add-authtoken <your-token>
```

Add the tunnel to `~/Library/Application Support/ngrok/ngrok.yml`:

```yaml
version: "3"
agent:
  authtoken: <your-authtoken>
tunnels:
  things-mcp:
    addr: 8009
    proto: http
    host_header: localhost
    domain: <your-static-domain>.ngrok-free.dev   # free static domain from ngrok dashboard
```

Install the ngrok LaunchAgent (see `deploy/launchagents/` if one is added for your setup), or start manually:

```bash
ngrok start --all --config ~/Library/Application\ Support/ngrok/ngrok.yml
```

## Connecting Each Agent

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

Restart Claude Desktop after changing this file.

### Claude Mobile

In the Claude mobile app → Settings → MCP Servers → Add Server:

```
URL: https://<your-domain>.ngrok-free.dev/mcp
```

Note: the full `/mcp` path is required. The base domain alone returns 404.

### OpenClaw (local machine)

Use the local HTTP endpoint directly — no tunnel overhead:

```json
{
  "things": {
    "transport": "streamable-http",
    "url": "http://127.0.0.1:8009/mcp"
  }
}
```

### Hermes / Cursor / remote agents

Use the ngrok HTTPS URL:

```
https://<your-domain>.ngrok-free.dev/mcp
```

If the agent sends a Bearer token, configure `THINGS_MCP_REQUIRE_AUTH=true` in `.env` and set the token in `THINGS_AUTH_TOKEN`.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `THINGS_MCP_HOST` | `127.0.0.1` | Bind address |
| `THINGS_MCP_PORT` | `8009` | Port |
| `THINGS_AUTH_TOKEN` | — | **Required** for write operations |
| `THINGSDB` | (auto-detected) | Explicit path to `main.sqlite`; set in LaunchAgent plist to avoid glob at startup |
| `THINGS_MCP_REQUIRE_AUTH` | `false` | Enforce Bearer token on all requests |
| `THINGS_MCP_DEBUG` | `false` | Verbose console logging |

## Health Check

```bash
bash scripts/health-check.sh
```

Checks: LaunchAgent running, port 8009 responding, ngrok tunnel reachable, database file exists, Things 3 process running.

Override the ngrok domain:

```bash
THINGS_MCP_NGROK_DOMAIN=your-domain.ngrok-free.dev bash scripts/health-check.sh
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `unable to open database file` | `uv` missing Full Disk Access | Re-add `~/.local/bin/uv` to FDA in System Settings |
| Tools listed but all fail | Same as above or Things 3 not open | Grant FDA; open Things 3 |
| 404 on ngrok URL | Missing `/mcp` path | Use full URL: `https://domain.ngrok-free.dev/mcp` |
| Tunnel unreachable | ngrok not running | `launchctl kickstart -k gui/$(id -u)/com.nicoloorozco.ngrok` |
| Server not responding on 8009 | LaunchAgent stopped | `launchctl kickstart -k gui/$(id -u)/com.nicoloorozco.things-mcp-server` |

## Log Locations

```
~/.things-mcp-server.log   # stdout (session/request activity)
~/.things-mcp-server.err   # stderr (errors, stack traces)
~/.ngrok.log               # ngrok tunnel activity
```
