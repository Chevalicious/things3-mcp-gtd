# Publishing and approval: clients and registries

This page summarizes how **third-party surfaces** (n8n, ChatGPT/OpenAI, ClawdHub) relate to **self-hosted** MCP servers like Things MCP. Processes and names change; always follow the vendor’s current documentation.

## n8n

- **Node documentation:** [MCP Client Tool](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp)
- **Listing:** Using an MCP server in a workflow does not require publishing to an “n8n store.” You deploy the server and reference its URL in your instance.
- **Community nodes:** Things MCP is not a community node; it is an external server you run.

## ChatGPT / OpenAI

- **Docs:** [MCP concepts for apps](https://developers.openai.com/apps-sdk/concepts/mcp-server/), [Connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/)
- **Approval:** OpenAI controls which apps appear inside ChatGPT and may require review for public distribution. Self-hosted or private URLs follow OpenAI’s current developer program rules.
- **Requirements:** HTTPS endpoint for remote access, strict JSON Schema expectations (see [chatgpt-fastmcp-compatibility.md](chatgpt-fastmcp-compatibility.md)).

## OpenClaw (Clawdbot) and ClawdHub

- **OpenClaw:** Open-source gateway; no app-store approval for registering `mcp.servers` in your own config.
- **ClawdHub:** Registry for **skills** and related bundles. Publishing a skill (often a `SKILL.md` with YAML frontmatter plus supporting files) is documented in OpenClaw’s tooling docs, for example [ClawdHub](https://docs.openclaw.ai/tools/clawhub.md) and [Creating skills](https://docs.openclaw.ai/tools/creating-skills.md). Exact CLI commands (`npx clawdhub@latest …`) may change; follow the official page.

## Things MCP repository

- **Issues and contributions:** [GitHub Issues](https://github.com/CaseyRo/mcp-things/issues)
- **License:** MIT — see [LICENSE](../LICENSE)

## Checklist before publishing a skill or app that wraps Things MCP

1. **Security:** Do not expose unauthenticated write access to Things data.
2. **Platform:** macOS + Things 3 + URL token must be clear to users.
3. **Compatibility:** Point readers at [integration-n8n.md](integration-n8n.md), [integration-chatgpt.md](integration-chatgpt.md), or [integration-clawdbot.md](integration-clawdbot.md) as appropriate.
