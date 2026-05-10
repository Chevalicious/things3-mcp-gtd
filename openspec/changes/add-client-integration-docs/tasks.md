# Tasks: Add Client Integration Documentation

## 1. Research and Gather Information

- [x] 1.1 Research n8n MCP Client Tool official documentation and integration requirements
- [x] 1.2 Research ChatGPT MCP integration official documentation and requirements
- [x] 1.3 Research clawdbot MCP integration official documentation and requirements
- [x] 1.4 Research approval/listing processes for n8n extensions directory (if applicable)
- [x] 1.5 Research approval/listing processes for ChatGPT MCP server directory (if applicable)
- [x] 1.6 Research ClawdHub (<https://clawdhub.com/>) skill publishing process and requirements
- [x] 1.6.1 Research SKILL.md format requirements (frontmatter: name, description, optional metadata)
- [x] 1.6.2 Research ClawdHub CLI publishing commands (`clawdhub publish` or similar)
- [x] 1.6.3 Research skill bundle structure (SKILL.md + supporting files)
- [x] 1.7 Review existing compatibility docs (`docs/n8n-fastmcp-compatibility.md`, `docs/chatgpt-fastmcp-compatibility.md`) for technical details to reference

## 2. Create n8n Integration Guide

- [x] 2.1 Create `docs/integration-n8n.md` with:
  - Overview of n8n MCP Client Tool integration
  - Prerequisites (n8n version, MCP Client Tool node availability)
  - Step-by-step setup instructions
  - Configuration details (server URL, transport type)
  - Link to official n8n MCP documentation
  - Troubleshooting section referencing compatibility guide
- [x] 2.2 Include screenshots or examples of n8n workflow configuration (if applicable) — text-only; no screenshots in-repo
- [x] 2.3 Cross-reference `docs/n8n-fastmcp-compatibility.md` for technical details

## 3. Create ChatGPT Integration Guide

- [x] 3.1 Create `docs/integration-chatgpt.md` with:
  - Overview of ChatGPT MCP integration
  - Prerequisites (ChatGPT account, MCP support)
  - Step-by-step setup instructions
  - Configuration details (server URL, HTTPS requirements, transport type)
  - Link to official OpenAI/ChatGPT MCP documentation
  - Troubleshooting section referencing compatibility guide
- [x] 3.2 Include information about HTTPS requirements (ngrok or similar)
- [x] 3.3 Cross-reference `docs/chatgpt-fastmcp-compatibility.md` for technical details

## 4. Create clawdbot Integration Guide

- [x] 4.1 Create `docs/integration-clawdbot.md` with:
  - Overview of clawdbot MCP integration
  - Prerequisites (clawdbot installation/access)
  - Step-by-step setup instructions
  - Configuration details (server URL, transport type)
  - Link to official clawdbot documentation (<https://docs.clawd.bot/>)
  - Troubleshooting section
- [x] 4.2 Include information about ClawdHub skill registry and how to install skills
- [x] 4.3 Include examples of configuration and setup
- [x] 4.4 Include information about installing skills via `npx clawdhub@latest install <skill-name>`

## 5. Create Integration Approval Guide

- [x] 5.1 Create `docs/integration-approval.md` with:
  - Overview of approval/listing processes for each client
  - n8n approval process (if applicable - check for extensions directory)
  - ChatGPT approval process (if applicable - check for MCP server directory)
  - ClawdHub skill publishing process (<https://clawdhub.com/>) - how to publish skills to the registry
  - SKILL.md format requirements (YAML frontmatter with name, description, optional metadata)
  - Skill bundle structure (SKILL.md + supporting files)
  - ClawdHub CLI commands for publishing (`npx clawdhub@latest publish` or similar)
  - Requirements checklist for each platform
  - Submission guidelines and links
  - Timeline expectations
  - Tips for successful approval and skill publishing

## 6. Update README.md

- [x] 6.1 Add new "Client Integration" section to README.md linking to all integration guides
- [x] 6.2 Remove or update any existing Claude Desktop references to point to clawdbot guide
- [x] 6.3 Add links to integration guides in Quick Start section
- [x] 6.4 Ensure consistency with existing documentation style

## 7. Update Other Documentation

- [x] 7.1 Update `CLAUDE.md` (repository root) to reference new integration guides
- [x] 7.2 Update `docs/DEVELOPERS.md` to reference new integration guides (if applicable)
- [x] 7.3 Ensure cross-references between compatibility guides and integration guides

## 8. Validation

- [x] 8.1 Review all documentation for accuracy and completeness
- [x] 8.2 Verify all official documentation links are correct and accessible
- [x] 8.3 Test integration steps (if possible) to ensure accuracy — manual verification on macOS still required for full E2E
- [x] 8.4 Check markdown formatting and consistency
- [x] 8.5 Run `ruff check` and `ruff format` on any code examples in docs

## 9. Final Review

- [x] 9.1 Review documentation structure and organization
- [x] 9.2 Ensure all links work correctly
- [x] 9.3 Verify approval process information is accurate and up-to-date
- [x] 9.4 Check that documentation follows project conventions
