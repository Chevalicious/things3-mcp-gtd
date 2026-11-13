# Testing with Things 3

The default `uv run --locked pytest` suite does not access your Things data. For a live, non-mutating check, start the client in read-only mode and call `get-tasks` or `get-projects`.

The live tests make real changes, including creating tags. Run them only in a disposable macOS/Things profile with Things URLs enabled and the Things token set in the environment:

```sh
THINGS_MCP_LIVE_TESTS=1 THINGS_MCP_ALLOW_TAG_CREATION=true uv run --locked pytest -m real
```

Live cleanup only targets recorded test IDs. A failed test or delayed write can leave a test item behind; clean it up in the app on the disposable profile. Don't run live tests against your regular task library.


For a targeted smoke test with a clean wheel, use a uniquely named disposable project, heading, and Inbox to-do. Keep tag creation disabled. Use two fresh stdio client sessions: capture the to-do, move it by ID into an area and project, reconnect, then move it into the heading and back to the project root. Check the returned ID and inspect the destination in Things. Move the disposable project and its tasks to Trash after testing; do not empty Trash. Verify separately that the installed HTTP command challenges unauthenticated requests, rejects foreign origins, and hides and blocks write tools in read-only mode.

## Compact reads and Inbox batch receipts

Run the default suite on Python 3.12 and 3.14. The MCP regressions use synthetic notes, checklist rows, and tags. They check compact and detailed text, heading IDs, note matching, one create-only URL, malformed or oversized batches, unknown tags, partial readback, ambiguous matches, uncertain handoff, and the read-only gate.

Build a wheel and install it into a fresh environment on each Python version. Start its installed `things3-mcp` command over stdio and loopback HTTP. Initialize each transport, list tools, and call `get-cache-stats`. In read-only mode verify `capture-tasks` is absent and a direct call is rejected. With a separate HTTP bearer token, verify the bearer challenge and rejection of foreign Host and Origin headers.

For live verification, keep tag creation off and use two fresh stdio sessions with the same installed client. Capture disposable Inbox rows and compare confirmed IDs with the exact items in Things. Use a uniquely named scheduled to-do to check the reminder date and time, formatted notes, and native checklist in the app. Use a disposable project and heading to verify placement if testing moves. Check for permission prompts on both launches. Move only the verified fixtures to Trash and confirm none remain active.
