# Things 3 MCP

Connect an MCP client to Things 3 on your Mac. Find tasks, capture to-dos, edit schedules and checklists, plan projects, and review what's coming up. Use the lists and tags you already have.

The server runs on your Mac. It reads the Things database in read-only mode and uses the official Things URL scheme for routine writes. Task data goes to the MCP client you connect. Unofficial; not affiliated with Cultured Code.

## Agent Usage

### 1. Requirements

- A Mac with Things 3, opened at least once under the macOS account that will run the server
- An MCP client on the same Mac
- [uv](https://docs.astral.sh/uv/getting-started/installation/), or Python 3.12 or newer

### 2. Install

```sh
uv tool install things3-mcp-gtd
```

```sh
command -v things3-mcp
```

Copy the absolute path the second command prints. GUI apps often have a different `PATH` than Terminal, so clients need the full path. The older `things3-mcp-gtd` command is still installed and behaves the same.

### 3. Add the server to your client (read-only)

Add a **stdio** server in your client's MCP settings. For clients that use an `mcpServers` JSON object:

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

Restart or reload the client.

### 4. Verify

1. Call `get-cache-stats`. A reply means the client reached the server.
2. Call `get-tasks` with `{"view":"today"}`. A task list means the server can read Things.

If the second call fails, see [Permissions](#permissions).

### 5. Enable writes (optional)

1. In Things, open **Settings → General** and turn on **Enable Things URLs**. Do this before the next step; otherwise Things asks the first time it receives a URL.
2. Remove `THINGS_MCP_READ_ONLY` from the server's `env` and reload the client. Creating to-dos and projects now works.
3. To change existing items (complete, move, reschedule, edit), click **Manage** next to Enable Things URLs, copy the token, and add it as `THINGS_AUTH_TOKEN` in the server's `env`. Keep it out of prompts and source control.

## Permissions

The server asks for as little as it can, and each grant is made once.

| What you do | What it needs | Where you grant it |
| --- | --- | --- |
| Read tasks | Access to the Things app container for the app that launches the server | macOS prompt on first read |
| Create to-dos and projects | Things URLs enabled | Things → Settings → General |
| Change existing items | `THINGS_AUTH_TOKEN` | Server environment |
| Create missing tags (off by default) | macOS Automation permission to control Things | macOS prompt on first use |
| Create areas or move tasks to Trash (off by default) | macOS Automation permission to control Things | macOS prompt on first use |

To keep macOS from asking again, keep using the same client and the same installed `things3-mcp` path. macOS ties its grants to the launching app, so a different client, terminal, or reinstalled path may be asked once more. If reads fail, check that launcher's permission in **System Settings → Privacy & Security**.

The server never needs Accessibility access, and it doesn't start or probe Things when it launches. Routine reads, writes, and use of existing tags don't use AppleScript.

If a tool reports an unknown tag, create it in **Things → Window → Tags** and retry. This includes the `waiting-for` tag used by `delegate-task`. Set `THINGS_MCP_ALLOW_TAG_CREATION=true` to let the server create missing tags, or `THINGS_MCP_ALLOW_AUTOMATION_WRITES=true` for local area creation and Trash. These AppleScript tools may trigger the [Automation prompt](https://support.apple.com/guide/mac-help/mchl108e1718/mac).

## Settings

Set these in your client's `env` block, or in an owner-only `.env` file in the server's working directory. See [.env.example](.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `THINGS_MCP_READ_ONLY` | `false` | Hide and block every tool that writes or opens Things |
| `THINGS_AUTH_TOKEN` | unset | Things URL token; required only to change existing items |
| `THINGS_MCP_ALLOW_TAG_CREATION` | `false` | Create missing tags through AppleScript |
| `THINGS_MCP_ALLOW_AUTOMATION_WRITES` | `false` | Enable local area creation and Trash through AppleScript |
| `THINGS_MCP_TRANSPORT` | `streamable-http` | `stdio` or `streamable-http`; `--transport` overrides it |
| `THINGS_MCP_HOST` | `127.0.0.1` | HTTP bind address; loopback only |
| `THINGS_MCP_PORT` | `8009` | HTTP port |
| `THINGS_MCP_HTTP_TOKEN` | unset | Bearer credential for the HTTP endpoint (32+ characters) |
| `THINGS_MCP_REQUIRE_AUTH` | `false` | Refuse to start HTTP without `THINGS_MCP_HTTP_TOKEN` |
| `THINGS_MCP_DEBUG` | `false` | Verbose logging to stderr |

## Local HTTP instead of stdio

If your client takes a URL instead of a command, start the server yourself:

```sh
THINGS_MCP_READ_ONLY=true things3-mcp --transport streamable-http
```

Set the client endpoint to `http://127.0.0.1:8009/mcp`. The server listens on loopback only and rejects browser origins and foreign `Host` headers.

On a shared Mac, generate a credential with `openssl rand -hex 32`, set it as `THINGS_MCP_HTTP_TOKEN` in the server environment, and send it from your client as an `Authorization: Bearer …` header. Never reuse your Things URL token as the HTTP credential.

For remote agents that connect through a browser approval flow, see [optional OAuth setup](docs/OAUTH.md).

## Tools

| What you want to do | Tools |
| --- | --- |
| Find tasks or choose what to work on | `get-tasks`, `search-tasks`, `focus-mode`, `process-inbox` |
| Browse lists and tags | `get-projects`, `get-areas`, `get-tags` |
| Create | `capture-task`, `capture-tasks`, `schedule-task` |
| Change an existing to-do | `modify-task`, `move-task`, `organize-task`, `complete-task`, `cancel-task`, `defer-task`, `delegate-task` |
| Plan a project | `plan-project`, `convert-to-project` |
| Review activity | `daily-review`, `weekly-review` |
| Open Things or check the connection | `show-in-app`, `get-cache-stats`, `things-health`, `diagnose` |
| Create an area or move a to-do to Trash (local opt-in) | `create-area`, `trash-task` |

### Read task details

`get-tasks`, `search-tasks`, `focus-mode`, and `process-inbox` return compact rows by default: task ID, status, dates, and destination, including heading IDs. Set `include_details` to `true` for notes, tags, native checklist rows, and a local Things link.

```json
{"query":"venue deposit","include_details":true}
```

Search matches notes in either mode.

### Capture a small Inbox batch

Call `capture-tasks` with a `tasks` array of up to 10 rows. Each row takes a single-line title, optional notes, and optional existing tag names.

```json
{"tasks":[{"title":"Call the venue","notes":"Ask about Friday availability."},{"title":"Print the agenda"}]}
```

The whole batch is checked before anything is sent; fix any reported row and submit again. After sending, each row is reported as confirmed with its new ID, or unconfirmed. The server sends a batch once and never replays it, so check Things before retrying an unconfirmed row.

### Schedule with a formatted note and checklist

```json
{
  "title": "Prepare for the site visit",
  "when": "tomorrow@09:00",
  "notes": "## Visit notes\n- **Bring ID**\n- Read the *visitor guide*: https://example.com/visitors",
  "checklist": ["Confirm arrival time", "Print directions"]
}
```

`when` takes the native Things schedule string. Use `checklist` for native checklist rows; a Markdown checkbox stays in the note as text. Things ignores a time for `anytime` and `someday`, and Things URLs can't reschedule a repeating to-do. See the [Things Markdown guide](https://culturedcode.com/things/support/articles/4651820/) and [Things URL scheme](https://culturedcode.com/things/support/articles/2803573/) for supported formats.

### Move a to-do

Call `move-task` with `task_id` and `destination_id` to file an existing to-do without making a copy. Get the task ID from `get-tasks` or `search-tasks`, project and heading IDs from `get-projects` with `{"include_items":true}`, and area IDs from `get-areas`. A project ID files the to-do at the top of the project; a heading ID files it under that heading.

### How writes are confirmed

Things URLs don't report back, so after a write the server reads the local database briefly to confirm it.

- Captures, scheduled to-dos, and new projects return the new ID when exactly one matching new item appears.
- Moves and completions return the existing ID once the requested state is visible.
- `convert-to-project` cancels the original only after it sees the new project.
- `modify-task`, `defer-task`, and `delegate-task` report that the request was submitted; open the task to verify.

If a response says a write was submitted but not confirmed, check Things before retrying. Things can ignore unsupported fields or take longer than the confirmation window.

## Privacy

The server has no telemetry and writes no log file. Task titles, notes, and destinations returned by tools go to your MCP client; if that client uses a remote AI service, the service can receive them. Compact results still include titles and destinations. See [Privacy](PRIVACY.md) and [Terms of Use](TERMS_OF_USE.md).

Reads use [things.py](https://github.com/thingsapi/things.py) against the Things SQLite database in read-only mode. This relies on Things' private database format and may need an update after a Things release. Writes never touch SQL.

## Upgrading from 1.x

- Use stdio or loopback HTTP for local clients. For remote clients, use the new [optional OAuth transport](docs/OAUTH.md). If you exposed the legacy OAuth endpoints, rotate your Things URL token in Things before switching.
- Tag creation is now off by default. Create tags in Things, or set `THINGS_MCP_ALLOW_TAG_CREATION=true`.
- Task lists are compact by default. Pass `include_details: true` for notes, tags, and checklists.
- Legacy scheduling and filing arguments are supported. Tools that use AppleScript require an explicit opt-in.

---

[Development and testing](docs/DEVELOPERS.md) · [Changelog](CHANGELOG.md) · [MIT License](LICENSE)
