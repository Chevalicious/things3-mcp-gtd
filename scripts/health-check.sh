#!/bin/bash
# Quick health check for the Things MCP server (and an optional ngrok tunnel).
#
# Usage:
#   bash scripts/health-check.sh
#
# Configuration (env vars):
#   THINGS_MCP_HOST        Default: localhost
#   THINGS_MCP_PORT        Default: 8009
#   THINGS_MCP_NGROK_DOMAIN  Optional. If set, the tunnel reachability check
#                            runs against this domain. If unset, that check is
#                            skipped.
#
# Exit code 0 = all green, 1 = one or more checks failed.

HOST="${THINGS_MCP_HOST:-localhost}"
PORT="${THINGS_MCP_PORT:-8009}"
NGROK_DOMAIN="${THINGS_MCP_NGROK_DOMAIN:-}"
FAIL=0

INIT_PAYLOAD='{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1"}},"id":1}'

echo "=== Things MCP Health Check $(date) ==="

# 1. LaunchAgent process (macOS only; harmless skip elsewhere)
if command -v launchctl >/dev/null 2>&1; then
  PID=$(launchctl list 2>/dev/null | awk '/things-mcp-server/{print $1}')
  if [ -n "$PID" ] && [ "$PID" != "-" ]; then
    echo "[OK ] FastMCP server running (PID $PID)"
  else
    echo "[ERR] FastMCP server not running. Load your LaunchAgent, e.g.:"
    echo "      launchctl load ~/Library/LaunchAgents/<your-launchagent>.plist"
    FAIL=1
  fi
else
  echo "[SKIP] launchctl not available; skipping LaunchAgent check"
fi

# 2. Local port responds to an MCP initialize
curl -sf -X POST "http://${HOST}:${PORT}/mcp" \
  -H "Content-Type: application/json" \
  -d "$INIT_PAYLOAD" \
  > /dev/null 2>&1 \
  && echo "[OK ] http://${HOST}:${PORT}/mcp responding" \
  || { echo "[ERR] http://${HOST}:${PORT}/mcp not responding"; FAIL=1; }

# 3. Optional: ngrok tunnel reachability
if [ -n "$NGROK_DOMAIN" ]; then
  curl -sf -X POST "https://${NGROK_DOMAIN}/mcp" \
    -H "Content-Type: application/json" \
    -d "$INIT_PAYLOAD" \
    > /dev/null 2>&1 \
    && echo "[OK ] ngrok tunnel reachable (${NGROK_DOMAIN})" \
    || { echo "[ERR] ngrok tunnel unreachable (${NGROK_DOMAIN})"; FAIL=1; }
else
  echo "[SKIP] THINGS_MCP_NGROK_DOMAIN not set; skipping tunnel check"
fi

# 4. Things database file (macOS only)
if [ "$(uname -s)" = "Darwin" ]; then
  CONTAINER="$HOME/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac"
  DB=$(ls "$CONTAINER"/ThingsData-*/Things\ Database.thingsdatabase/main.sqlite 2>/dev/null | head -n 1)
  if [ -n "$DB" ] && [ -f "$DB" ]; then
    echo "[OK ] Things database found: $DB"
  else
    echo "[ERR] Things database not found under $CONTAINER/ThingsData-*"
    FAIL=1
  fi

  # 5. Things 3 process (needed for URL-scheme writes)
  pgrep -x "Things3" > /dev/null \
    && echo "[OK ] Things 3 running" \
    || echo "[WRN] Things 3 not running; write tools will fail until launched"

  # 6. Apple Event system responsive (a hung AE can freeze the server)
  if command -v osascript >/dev/null 2>&1; then
    timeout 4 osascript -e 'tell application "Things3" to return name' > /dev/null 2>&1 \
      && echo "[OK ] Apple Events responding" \
      || echo "[WRN] Apple Events hung or Things 3 not running. See docs/runbook-recovery.md"
  fi
fi

echo "==================================="
exit $FAIL
