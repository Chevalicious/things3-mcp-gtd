# OpenClaw Restoration: MiniMax M2.7 Migration
**Date:** 2026-03-26

---

## Root Cause

Kimi k2p5 had a model-level degradation causing it to emit `arguments: {}` on tool calls (no parameters filled in). This is not a config issue — the model itself broke, failing to populate required parameters like `path`, `command`, etc. for any tool call not phrased in an exact recognized format.

---

## What Was Changed

### `~/.openclaw/openclaw.json`
- Added MiniMax provider definition (`baseUrl: https://api.minimax.io/v1`, `api: openai-completions`)
- Added models: `MiniMax-M2.7-highspeed` (fast mode, primary) and `MiniMax-M2.7` (standard fallback)
- Switched default primary model from `kimi-coding/k2p5` → `minimax/MiniMax-M2.7-highspeed`
- Cleaned fallback chain — removed:
  - `kimi-coding:fallback/k2p5` (bogus debugging artifact)
  - `openrouter/google/gemini-2.0-flash-exp:free` (404 errors)
  - `openrouter/meta-llama/llama-3.3-70b-instruct:free` (deprecated)
- New fallback chain: `minimax/MiniMax-M2.7` → `groq/llama-3.3-70b-versatile` → `claude-cli/opus-4.6`
- Updated archivist agent model: `kimi-coding/k2p5` → `minimax/MiniMax-M2.7`
- Restored `claude-cli` CLI backend (was dropped from `cliBackends` during debugging)
- Added MiniMax auth profile: `minimax:default`

### `~/.openclaw/agents/main/agent/auth-profiles.json`
- Added `minimax:default` entry with API key

### `~/.openclaw/agents/archivist/agent/auth-profiles.json`
- Added `minimax:default` entry with API key

### `~/.zshrc`
- Added `MINIMAX_API_KEY` export (consistent with existing GROQ/KIMI key convention)

---

## Final Agent Model Assignment

| Agent | Model | Notes |
|-------|-------|-------|
| main (Larry) | `minimax/MiniMax-M2.7-highspeed` | Supervisor, inherits defaults |
| archivist | `minimax/MiniMax-M2.7` | Memory/GTD — standard mode sufficient |
| builder-bob | `groq/llama-3.3-70b-versatile` | Light coding, already working |
| scout | `groq/llama-3.3-70b-versatile` | Research, already working |
| cursor | inherits defaults | Heavy coding + MCP |

---

## Smoke Test Results

| Test | Command | Result |
|------|---------|--------|
| Model check | `"Say hello and tell me what model you're running on"` | ✅ `minimax/MiniMax-M2.7-highspeed` |
| Read tool (path param) | `"Read the first line of ~/.openclaw/openclaw.json"` | ✅ Returned `{` correctly |
| Exec tool (command param) | `"Run: date"` | ✅ Returned current date/time |

---

## Key Technical Note

API keys in OpenClaw are stored in per-agent `auth-profiles.json` files (not in `openclaw.json` and not in the macOS Keychain for this install). The gateway caches these on startup — a `openclaw daemon restart` is required after editing them.
