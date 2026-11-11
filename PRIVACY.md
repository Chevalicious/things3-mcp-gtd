# Privacy

Things 3 MCP runs under your macOS account. It can read Things tasks, notes, lists, tags, and related metadata and return them to its connected MCP client. If the client sends those results to an AI service, that service can receive the data. Connect only clients you trust and review their data settings.

Reads use SQLite in read-only mode. Writes use the Things URL scheme. Creating missing tags through AppleScript is separately opt-in. Enable `THINGS_MCP_READ_ONLY=true` to disable writes and opening the Things app through the server. The server has no built-in telemetry and doesn't create a log file by default. Treat client transcripts and any logs your launcher captures as private.

`THINGS_AUTH_TOKEN` authorizes updates inside Things. `THINGS_MCP_HTTP_TOKEN` controls access to the optional local HTTP endpoint. Keep these credentials separate and store them in your launcher’s private settings or an owner-only `.env`. macOS receives Things URLs through a short-lived helper process; another process with sufficient local privileges can inspect its arguments.

To remove credentials, remove the corresponding environment settings or `.env` values and restart the server. If upgrading, check whether an old `~/.things-mcp/config.json` or log directory remains; older versions could write those files. Rotate the Things URL token in the app if it may have been exposed. Avoid including real task data or credentials in issue reports.
