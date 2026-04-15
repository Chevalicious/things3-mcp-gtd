# ChatGPT integration

Use Things MCP with **ChatGPT apps** (formerly “connectors”) that speak MCP over **HTTPS**. ChatGPT expects a remote MCP endpoint; your Things MCP process is local HTTP, so you typically expose it with a TLS tunnel (for example ngrok, Cloudflare Tunnel, or local HTTPS reverse proxy).

## Prerequisites

- ChatGPT with **developer mode** and **apps** (MCP) enabled for your workspace (see OpenAI’s current Apps SDK docs).
- **macOS + Things 3** on the machine where the MCP server runs.
- **Public HTTPS URL** whose path forwards to your server’s `/mcp` endpoint.

## Official documentation

- [MCP for ChatGPT apps and API](https://developers.openai.com/apps-sdk/concepts/mcp-server/) — concepts
- [Build your MCP server](https://developers.openai.com/apps-sdk/build/mcp-server/) — implementation notes
- [Connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/) — wiring an app to ChatGPT

## Transport and URL

- This server uses **streamable HTTP** only; the MCP path is **`/mcp`**.
- Locally: `http://127.0.0.1:8009/mcp`
- For ChatGPT: configure the app with an **HTTPS** base URL that terminates TLS and proxies to `http://127.0.0.1:8009` so that **`https://your-host/...`** maps to the same JSON-RPC streamable HTTP MCP session your local clients use.

Exact UI labels change over time; follow OpenAI’s “Connect from ChatGPT” guide for creating the app and pasting the MCP URL.

## HTTPS tunnel (example)

1. Run Things MCP: `uv run server`
2. Start a tunnel from a public HTTPS URL to port `8009` (example providers: ngrok, Cloudflare Tunnel, localhost.run).
3. In ChatGPT app settings, set the MCP endpoint to `https://<tunnel-host>/mcp` (or the path your tunnel maps to `/mcp`).

**Security:** exposing the server increases attack surface. Use tunnel auth, IP allowlists, or a reverse proxy with authentication. Do not expose write tools without understanding the risk to your Things data.

## Strict JSON Schema

ChatGPT’s tool-calling stack can require **strict** JSON Schema (for example `additionalProperties: false` and every property listed under `required`). This server applies ChatGPT-oriented transforms when it detects ChatGPT via `User-Agent`. Details: [ChatGPT + FastMCP compatibility](chatgpt-fastmcp-compatibility.md).

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| Schema rejected / “additionalProperties” errors | Confirm you are on a recent Things MCP release with ChatGPT transforms. See [chatgpt-fastmcp-compatibility.md](chatgpt-fastmcp-compatibility.md). |
| Cannot connect | Verify HTTPS URL, tunnel running, and path matches `/mcp`. |
| Writes do nothing | Set `THINGS_AUTH_TOKEN` in the server environment (Things → Settings → General → Things URLs). |

## See also

- [ChatGPT + FastMCP compatibility](chatgpt-fastmcp-compatibility.md)
