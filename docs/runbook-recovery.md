# Recovery Runbook — Apple Event Hang

**Symptom:** The server accepts TCP connections but never returns an HTTP
response. `bash scripts/health-check.sh` reports the local port as not
responding even though the LaunchAgent process is alive.

**Root cause:** The macOS Apple Event (AE) subsystem became hung. `osascript`
entered an uninterruptible D-state, blocking the asyncio event loop.

## Recovery steps (in order)

1. **Open Things 3 from the Dock** (or `open -a Things3` in Terminal). This
   uses a different launch path that can wake the AE daemon. Wait 10–15 s
   and rerun `bash scripts/health-check.sh`.

2. **Send a URL-scheme open** to bypass `osascript` entirely:

   ```bash
   open "things:///show?id=inbox"
   ```

   Wait 10 s and re-check.

3. **Restart the server through the LaunchAgent.** The `-k` flag kills the
   current process and starts a fresh one, which the LaunchAgent then keeps
   alive:

   ```bash
   launchctl kickstart -k gui/$(id -u)/com.things-mcp-server
   ```

   This is the sanctioned restart path. **Do not** run `uv run server`
   directly to "restart" — that creates a second instance and reintroduces
   the port-conflict crash loop.

4. **Last resort: reboot.** A hard AE hang that survives all of the above
   requires a macOS restart to reset the IPC infrastructure.

## Why direct `uv run server` is dangerous when a LaunchAgent is loaded

The LaunchAgent owns port 8009 and re-spawns the server if it dies. A
manually-started second instance will fail to bind, exit, and the
LaunchAgent will immediately restart its own copy — which can itself fail
to bind if the manual instance briefly succeeded. The result is a tight
crash-restart loop that triggers repeated macOS "uv would like to access
data from other apps" permission dialogs.

`launchctl kickstart -k` avoids this because it operates *through* the
LaunchAgent rather than around it.
