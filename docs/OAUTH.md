# Connect a remote MCP client

The OAuth transport runs on loopback on the Mac that runs Things. A dedicated HTTPS reverse proxy or tunnel forwards the hostname to that listener. Run it on a separate port if the Mac already has a local HTTP service. Local stdio does not need OAuth.

1. Create a GitHub OAuth App for this endpoint. Set its homepage to your HTTPS origin and its authorization callback to `https://your-host/auth/callback`. Use a dedicated app for this Things installation.
2. Set the following in the launcher's private environment. Use the numeric account ID of the GitHub account that may access Things. While signed in to the correct GitHub account, you can get it with `gh api user --jq .id`. For the client callbacks, use the redirect URLs provided by the MCP client. Multiple values are comma-separated.

   ```dotenv
   THINGS_MCP_OAUTH_URL=https://your-host
   THINGS_MCP_OAUTH_GITHUB_CLIENT_ID=your-client-id
   THINGS_MCP_OAUTH_GITHUB_CLIENT_SECRET=your-client-secret
   THINGS_MCP_OAUTH_GITHUB_USER_ID=your-numeric-account-id
   THINGS_MCP_OAUTH_REDIRECT_URIS=https://agent.example/oauth/callback
   THINGS_MCP_PORT=8010
   ```

3. Start `things3-mcp --transport oauth-http` and forward the dedicated HTTPS origin to `http://127.0.0.1:8010`. Preserve the public Host header and forward all paths on that origin so OAuth discovery, callback, and MCP routes work. Use a stable launcher and macOS account to retain the local database permission and FastMCP's encrypted OAuth state.
4. In an MCP client that supports OAuth registration and PKCE, add `https://your-host/mcp`, click Connect, and approve access using the configured GitHub account. Verify with `things-health` and `get-tasks`. Client support and callback URLs vary by product.

Remote access defaults to read-only. Set `THINGS_MCP_OAUTH_ALLOW_WRITES=true` only if every approved client on that listener should be able to write. `THINGS_MCP_READ_ONLY=true` takes precedence. Existing-item writes still use the local `THINGS_AUTH_TOKEN`. Area creation and Trash are local-only. To revoke access for this endpoint, stop the listener or revoke its OAuth app authorization from your GitHub account. Existing client connections depend on the app authorization, client behavior, and the configured OAuth secret.
