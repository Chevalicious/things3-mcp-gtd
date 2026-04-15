"""OAuth 2.0 Authorization Server for Things MCP.

Implements RFC 6749 (Authorization Code grant) + RFC 7636 (PKCE) so that
Claude Desktop can authenticate via the "Add URL" flow without any changes
to claude_desktop_config.json.

Flow:
1. Claude Desktop hits /mcp → gets 401 with WWW-Authenticate: Bearer
2. Claude Desktop fetches /.well-known/oauth-authorization-server
3. Browser opens /authorize → user clicks "Allow"
4. POST /authorize issues a short-lived code, redirects to Claude's callback
5. Claude Desktop POSTs /token → gets THINGS_AUTH_TOKEN as bearer token
6. All subsequent /mcp requests include Authorization: Bearer <token>
"""

import base64
import hashlib
import html
import secrets
import time

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from .logging_config import get_logger
from .settings import get_auth_token

logger = get_logger(__name__)

# In-memory store: code → {redirect_uri, code_challenge, expires}
_auth_codes: dict[str, dict] = {}

CODE_TTL = 300  # 5 minutes


def _base_url(request: Request) -> str:
    """Reconstruct the public base URL from the incoming request."""
    # Respect X-Forwarded-Proto / X-Forwarded-Host set by ngrok
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}"


async def protected_resource_metadata(request: Request) -> JSONResponse:
    """RFC 8707 Protected Resource Metadata — GET /.well-known/oauth-protected-resource

    Claude Desktop requests this first (MCP spec 2025-03-26) to discover which
    authorization server handles this resource.
    """
    base = _base_url(request)
    return JSONResponse(
        {
            "resource": base,
            "authorization_servers": [base],
        }
    )


async def oauth_metadata(request: Request) -> JSONResponse:
    """RFC 8414 Authorization Server Metadata — GET /.well-known/oauth-authorization-server"""
    base = _base_url(request)
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/authorize",
            "token_endpoint": f"{base}/token",
            "registration_endpoint": f"{base}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }
    )


async def client_registration(request: Request) -> JSONResponse:
    """RFC 7591 Dynamic Client Registration — POST /register

    MCP spec (2025-03-26) requires clients to register before starting the
    authorization flow. We accept any registration and issue a client_id.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    client_id = secrets.token_urlsafe(16)
    logger.info("OAuth: dynamic client registered (client_id=%s)", client_id)
    return JSONResponse(
        {
            "client_id": client_id,
            "client_id_issued_at": int(time.time()),
            "redirect_uris": body.get("redirect_uris", []),
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
        },
        status_code=201,
    )


async def authorize_get(request: Request) -> HTMLResponse:
    """Show authorization approval page — GET /authorize"""
    client_id = html.escape(request.query_params.get("client_id", ""))
    redirect_uri = html.escape(request.query_params.get("redirect_uri", ""))
    state = html.escape(request.query_params.get("state", ""))
    code_challenge = html.escape(request.query_params.get("code_challenge", ""))
    code_challenge_method = html.escape(
        request.query_params.get("code_challenge_method", "S256")
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Things MCP — Authorize</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f2f2f7;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }}
    .card {{
      background: white;
      border-radius: 16px;
      padding: 40px 36px;
      max-width: 400px;
      width: 100%;
      box-shadow: 0 4px 24px rgba(0,0,0,.08);
      text-align: center;
    }}
    .icon {{ font-size: 48px; margin-bottom: 16px; }}
    h1 {{ font-size: 22px; font-weight: 600; color: #1c1c1e; margin-bottom: 8px; }}
    p {{ font-size: 15px; color: #6e6e73; line-height: 1.5; margin-bottom: 28px; }}
    .btn {{
      display: inline-block;
      background: #007AFF;
      color: white;
      border: none;
      padding: 14px 32px;
      border-radius: 10px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      transition: background .15s;
    }}
    .btn:hover {{ background: #0066cc; }}
    .app {{ font-size: 13px; color: #aeaeb2; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">📝</div>
    <h1>Connect to Things 3</h1>
    <p>An application wants to access your Things 3 tasks via the MCP server.</p>
    <form method="POST" action="/authorize">
      <input type="hidden" name="client_id" value="{client_id}">
      <input type="hidden" name="redirect_uri" value="{redirect_uri}">
      <input type="hidden" name="state" value="{state}">
      <input type="hidden" name="code_challenge" value="{code_challenge}">
      <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
      <button type="submit" class="btn">Allow Access</button>
    </form>
    <p class="app">Things MCP Server</p>
  </div>
</body>
</html>"""
    return HTMLResponse(page)


async def authorize_post(request: Request) -> RedirectResponse:
    """Issue authorization code, redirect to client — POST /authorize"""
    form = await request.form()
    redirect_uri = str(form.get("redirect_uri", ""))
    state = str(form.get("state", ""))
    code_challenge = str(form.get("code_challenge", ""))
    code_challenge_method = str(form.get("code_challenge_method", "S256"))

    if not redirect_uri:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "redirect_uri required"},
            status_code=400,
        )

    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires": time.time() + CODE_TTL,
    }

    location = f"{redirect_uri}?code={code}"
    if state:
        location += f"&state={state}"

    logger.info("OAuth: authorization code issued (PKCE=%s)", bool(code_challenge))
    return RedirectResponse(location, status_code=302)


async def token(request: Request) -> JSONResponse:
    """Exchange authorization code for access token — POST /token"""
    # Support both form and JSON bodies
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        grant_type = body.get("grant_type", "")
        code = body.get("code", "")
        code_verifier = body.get("code_verifier", "")
        redirect_uri = str(body.get("redirect_uri") or "")
    else:
        form = await request.form()
        grant_type = str(form.get("grant_type", ""))
        code = str(form.get("code", ""))
        code_verifier = str(form.get("code_verifier", ""))
        redirect_uri = str(form.get("redirect_uri") or "")

    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    code_data = _auth_codes.pop(code, None)
    if not code_data:
        return JSONResponse(
            {
                "error": "invalid_grant",
                "error_description": "Unknown or already-used code",
            },
            status_code=400,
        )

    if time.time() > code_data["expires"]:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Code expired"},
            status_code=400,
        )

    stored_redirect = str(code_data.get("redirect_uri") or "")
    if not redirect_uri:
        return JSONResponse(
            {
                "error": "invalid_request",
                "error_description": "redirect_uri required",
            },
            status_code=400,
        )
    if redirect_uri != stored_redirect:
        return JSONResponse(
            {
                "error": "invalid_grant",
                "error_description": "redirect_uri mismatch",
            },
            status_code=400,
        )

    # Verify PKCE (S256)
    stored_challenge = code_data.get("code_challenge", "")
    if stored_challenge:
        if not code_verifier:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "code_verifier required",
                },
                status_code=400,
            )
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if computed != stored_challenge:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "PKCE verification failed",
                },
                status_code=400,
            )

    access_token = get_auth_token()
    if not access_token:
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "THINGS_AUTH_TOKEN not configured",
            },
            status_code=500,
        )

    logger.info("OAuth: access token issued successfully")
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 7_776_000,  # 90 days
        }
    )
