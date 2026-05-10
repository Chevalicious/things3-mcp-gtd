#!/bin/bash
# Quick health check for Things MCP server and ngrok tunnel.
# Usage: bash scripts/health-check.sh
# Exit code 0 = all green, 1 = one or more checks failed.

NGROK_DOMAIN="${THINGS_MCP_NGROK_DOMAIN:-somatogenic-claudine-vimineous.ngrok-free.dev}"
PORT="${THINGS_MCP_PORT:-8009}"
FAIL=0

echo "=== Things MCP Health Check $(date) ==="

# 1. LaunchAgent process
PID=$(launchctl list 2>/dev/null | awk '/things-mcp-server/{print $1}')
if [ -n "$PID" ] && [ "$PID" != "-" ]; then
  echo "[OK ] FastMCP server running (PID $PID)"
else
  echo "[ERR] FastMCP server not running — run: launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.things-mcp-server.plist"
  FAIL=1
fi

# 2. Port responding
curl -sf -X POST "http://127.0.0.1:${PORT}/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1"}},"id":1}' \
  > /dev/null 2>&1 \
  && echo "[OK ] Port ${PORT} responding" \
  || { echo "[ERR] Port ${PORT} not responding"; FAIL=1; }

# 3. ngrok tunnel (POST so ngrok doesn't redirect to browser challenge)
curl -sf -X POST "https://${NGROK_DOMAIN}/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1"}},"id":1}' \
  > /dev/null 2>&1 \
  && echo "[OK ] ngrok tunnel reachable (${NGROK_DOMAIN})" \
  || { echo "[ERR] ngrok tunnel unreachable — run: launchctl kickstart -k gui/$(id -u)/com.YOUR_USERNAME.ngrok"; FAIL=1; }

# 4. Database file
DB="$HOME/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-ZHBUE/Things Database.thingsdatabase/main.sqlite"
[ -f "$DB" ] \
  && echo "[OK ] Things database file exists" \
  || { echo "[ERR] Database not found: $DB"; FAIL=1; }

# 5. Things 3 process (needed for URL-scheme writes)
pgrep -x "Things3" > /dev/null \
  && echo "[OK ] Things 3 running" \
  || echo "[WRN] Things 3 not running — write tools will fail"

# 6. Apple Event system responsive (hung AE causes server to permanently freeze)
timeout 4 osascript -e 'tell application "Things3" to return name' > /dev/null 2>&1 \
  && echo "[OK ] Apple Events responding" \
  || { echo "[WRN] Apple Events hung or Things3 not running — open Things3 from Dock to recover, or: launchctl kickstart -k gui/$(id -u)/com.YOUR_USERNAME.things-mcp-server"; }

echo "==================================="
exit $FAIL
