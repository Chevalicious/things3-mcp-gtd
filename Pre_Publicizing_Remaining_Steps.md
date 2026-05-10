# Pre-Publicizing — Remaining Manual Steps

> **DELETE THIS FILE before tagging `v1.0.0`.** It exists only to track the
> handful of release steps that an autonomous agent cannot safely complete
> on its own.

This file lists everything I (the audit agent) intentionally **did not** do
in the public-release audit branch, and what you need to do once you've
merged the branch into `main`. Items are roughly ordered.

---

## Status of the audit

The PR `cursor/v1-0-0-public-release-audit-579b` already covers:

- **Phase 1 — Security & secrets scrub.** No live keys / tokens / passwords
  found. Personal infrastructure (ngrok subdomain, Tailscale IP, per-account
  Things data ID, maintainer-named LaunchAgent plist) replaced with
  placeholders.
- **Phase 2 — AI-slop & attribution sanitization.** Removed `CLAUDE.md`,
  `WEB_ACCESS_ROUTING.md`, `openclaw-minimax-migration-2026-03-26.md`, the
  duplicate root `things_fast_server.py`, and `docs/MIGRATION.md`. Slimmed
  `AGENTS.md` from 11 KB to a ~30-line orientation; recovery runbook moved
  to `docs/runbook-recovery.md`.
- **Phase 3 — Documentation overhaul.** Rewrote `README.md` (293 → ~175
  lines). Fixed the broken `cd mcp_things` instruction across all docs.
  Re-wrote `.env.example` with the correct env-var names. Synced
  `smithery.yaml` to the actual v2.0+ tool list. Patched the
  `mcp.server.fastmcp` import path in DEVELOPERS.md. Updated
  `openspec/project.md` module inventory.
- **Source cleanup.** Removed dead legacy wrappers from
  `src/things_mcp/config.py`, removed the dead `IconLike` shim from
  `src/things_mcp/server_core.py`, fixed the bad `from src.things_mcp`
  import in `scripts/configure_token.py`. Lint clean, format clean, all
  144 CI-safe tests pass.

---

## What's still on you

### 1. Review and merge the audit PR

The branch is `cursor/v1-0-0-public-release-audit-579b`. Read the diff in
each commit independently — they're scoped per phase so you can revert any
single one without losing the rest:

| # | Commit | Scope |
|---|---|---|
| 1 | `chore(release): remove off-topic and AI-workflow scaffolding files` | 5 file deletions |
| 2 | `chore(release): sanitize personal infrastructure and IP addresses` | ngrok / Tailscale IP / ZHBUE removal |
| 3 | `chore(release): align config templates and metadata with v2.0+ reality` | `.env.example`, `.gitignore`, `pyproject.toml`, `smithery.yaml` |
| 4 | `docs(release): rewrite README for v1.0.0 public release` | README only |
| 5 | `docs: fix branding, broken instructions, and stale architecture notes` | CHANGELOG, DEVELOPERS, openspec |
| 6 | `refactor(release): trim dead code paths from source` | `config.py`, `server_core.py`, `fast_server.py`, `configure_token.py`, format auto-fixes |

After merging, **delete this `Pre_Publicizing_Remaining_Steps.md` file**
in a follow-up commit (or as part of the v1.0.0-prep commit).

### 2. Decisions only you can make

The audit deliberately left these alone because they're personal-preference
or require your authorization:

- **Buy Me a Coffee badge** (`README.md`). I removed the badge in the
  rewrite. If you want it back, restore the line:
  ```markdown
  [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/caseyberlin)
  ```
  but be aware the URL contains `caseyberlin` (a personal handle).
- **Author list in `pyproject.toml` and `LICENSE`.** Currently lists
  Yaroslav Krempovych, Harald Lindstrøm, and Chevalicious with their
  GitHub `noreply` emails. Confirm this is what you want public.
- **Stale dev branches on `origin`.** These should probably be deleted from
  the public repo:
  ```bash
  git push origin --delete claude/add-email-explanation-7hKxH
  git push origin --delete claude/prepare-for-publishing-M5p5s
  git push origin --delete cursor/add-client-integration-docs-b853
  # 'source' branch: delete only if you've confirmed it isn't a workflow
  # target anywhere -- both main and source appear in .github/workflows/tests.yml
  ```
  After deleting `source`, also remove `source` from the `branches:` list in
  `.github/workflows/tests.yml`.
- **PyPI trusted publishing.** Pushing the `v1.0.0` tag will fire
  `.github/workflows/publish.yml`. Confirm the `pypi` GitHub Environment is
  configured with trusted publishing for the `things3-mcp-gtd` project
  before you push the tag, or temporarily disable that workflow.

### 3. IP addresses I intentionally did **not** replace

You asked me to replace all IP addresses with placeholders. I replaced
every IP literal in **user-facing documentation** (`docs/*.md`, README,
`.env.example`, `smithery.yaml`, `node-red-flow.json`). I also removed the
sensitive Tailscale IP (`100.93.89.102`) entirely. The following IP
literals were kept because changing them would alter runtime behavior:

| File | IP | Why kept |
|---|---|---|
| `src/things_mcp/settings.py:35` | `127.0.0.1` | Pydantic-settings field default for `things_mcp_host`. Replacing with the string `"localhost"` would change DNS resolution semantics on hosts where `localhost` doesn't map to `127.0.0.1` (e.g., dual-stack IPv6-first systems where it resolves to `::1`). Loopback IP literal is the safer default. |
| `src/things_mcp/server_core.py:114` | `127.0.0.1` | `DEFAULT_HOST` constant used in CLI startup logging. Same reasoning. |
| `tests/test_configuration.py:19, 60` | `127.0.0.1`, `192.168.1.1`, `0.0.0.0` | Test fixtures verifying that `Settings()` accepts these as valid host values. |
| `tests/test_server_startup.py:62` | `127.0.0.1` | Test fixture for an alternate-port server start. |
| `tests/test_mcp_protocol.py:68-69` | `127.0.0.1` | Test fixture for the MCPClient default endpoint. |
| `openspec/specs/server-testing/spec.md` and the `openspec/changes/archive/**` snapshots | `127.0.0.1` | Historical spec documents recording what defaults *were* at the time of writing. Editing archived OpenSpec changes would break their integrity. |

If you want **literally zero** IP addresses anywhere — including
breaking the above — say the word and I'll do a follow-up pass. My
recommendation is to keep them: `127.0.0.1` is universally understood as
loopback and is not personally identifying.

### 4. Phase 4 — git history reset to `v1.0.0` (NOT executed)

I did **not** run any of the destructive Phase 4 steps from the original
audit report. Phase 4 (orphan branch + force-push `main` + tag `v1.0.0`)
was explicitly conditioned on your "Block 5" go-ahead. Once you've merged
the audit PR, deleted this file, and confirmed everything looks right on
`main`, run the Phase 4 plan from the audit report. The full plan is
reproduced here for convenience:

#### Block 1 — safety net

```bash
cd /path/to/things3-mcp-gtd
git checkout main
git status                                         # must be clean
git tag -a pre-v1.0.0-history-snapshot -m "Snapshot of dev history immediately before v1.0.0 reset"
git branch backup/pre-v1.0.0-history main
git push origin pre-v1.0.0-history-snapshot
git push origin backup/pre-v1.0.0-history
# Verify both exist on the remote before continuing
git ls-remote --tags  origin | grep pre-v1.0.0-history-snapshot
git ls-remote --heads origin | grep backup/pre-v1.0.0-history
```

#### Block 2 — sanity check

```bash
git status                          # nothing to commit, working tree clean
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest tests -v    # CI-safe subset
```
**Stop and resolve any failures before continuing.**

#### Block 3 — orphan commit

```bash
git checkout --orphan release/v1.0.0
git add -A
git commit -m "Initial public release (v1.0.0)

Things 3 GTD MCP Server -- first public release.

A Model Context Protocol server for Things 3 on macOS that brings GTD
methodology to AI assistants. Exposes 13 GTD-native tools across the
five GTD stages (Capture, Clarify, Organize, Reflect, Engage) plus
utility search.

Built on FastMCP 3.x. macOS only.

Originally based on things-mcp by Harald Lindstrom
(https://github.com/hald/things-mcp); extended into a GTD-native server.
Full attribution preserved in LICENSE and pyproject.toml.
"
git log --oneline                           # exactly one line
git rev-list --count HEAD                   # 1
git cat-file -p HEAD | grep -c '^parent '   # 0
```

#### Block 4 — tag and verify

```bash
git tag -a v1.0.0 -m "v1.0.0 -- Initial public release"
# (optional, if you have a GPG key configured)
# git tag -s v1.0.0 -m "v1.0.0 -- Initial public release"
git rev-parse v1.0.0
git rev-parse HEAD                          # must match
uv build
ls dist/                                    # things3-mcp-gtd-1.0.0.tar.gz + .whl
```

#### Block 5 — replace `main` and push (DESTRUCTIVE)

```bash
git branch -M release/v1.0.0 main
git push --force-with-lease origin main
git push origin v1.0.0
# Optional: clean up dev branches (see section 2 above)
git ls-remote --heads origin
git ls-remote --tags  origin
```

### 5. Post-reset / post-tag checklist

Once `v1.0.0` is on the remote:

- [ ] **GitHub Release:** create a Release for the `v1.0.0` tag, body is
      the v1.0.0 entry in `CHANGELOG.md` (consolidate the `[Unreleased]`
      section into `[1.0.0]` first).
- [ ] **PyPI:** confirm the auto-publish workflow ran successfully on the
      tag push. If you opted to keep the workflow disabled, run
      `uv build && twine upload dist/*` manually.
- [ ] **Smithery:** re-submit / re-sync the registry entry now that
      `smithery.yaml` is corrected.
- [ ] **Repo settings:** flip the GitHub repo from private to public (if
      it isn't already). Enable Issues. Disable Wiki unless you intend to
      maintain it.
- [ ] **Optional cleanup after one healthy week:** delete
      `backup/pre-v1.0.0-history` from origin. Keep
      `pre-v1.0.0-history-snapshot` tag indefinitely.

### 6. Things I noticed but didn't fix

These are out of scope for the public-release audit but worth your
attention later:

- `src/things_mcp/fast_server.py:71-217` — the `_print_shutdown_summary()`
  ANSI-art shutdown banner is 147 lines of hand-rolled box drawing.
  Charming, but disproportionate to the entry point. Consider extracting
  to its own module (e.g. `_shutdown_banner.py`) post-1.0.
- `src/things_mcp/fast_server.py:418-431` — at startup the server tries
  to launch Things 3 via AppleScript. This is the documented cause of the
  Apple Event hang (`docs/runbook-recovery.md`). Consider gating it
  behind a config flag.
- `openspec/changes/archive/` — 10 archived change directories. Useful
  provenance, ~6 KB each, but bulky in repo browsers. Optionally move to
  `docs/archive/openspec/`.
- `docs/n8n-fastmcp-compatibility.md` and
  `docs/chatgpt-fastmcp-compatibility.md` mention recommendations
  upstream. Worth filing tracking issues if you want the upstream fixes.

---

## TL;DR

1. Review + merge `cursor/v1-0-0-public-release-audit-579b`.
2. Delete this file.
3. Decide: Buy Me a Coffee badge? PyPI auto-publish on or off? Stale dev
   branches deleted?
4. Execute Phase 4 (Blocks 1 → 5 above) when ready to publish.
5. Tick the post-reset checklist (GitHub Release, PyPI, Smithery, repo
   visibility).
