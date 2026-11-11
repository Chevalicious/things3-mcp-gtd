"""MCP tool registration and local Streamable HTTP transport."""

from hmac import compare_digest
import re

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route

from .client_compat import get_streamable_http_middleware
from .config import get_things_auth_token
from .server_core import create_mcp_server
from .settings import get_settings
from .tools_planning import register_planning_tools
from .tools_reviews import register_reviews_tools
from .tools_tasks import register_tasks_tools
from .tools_utility import register_utility_tools

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
LOCAL_AUTHORITY = re.compile(
    r"(?:127\.0\.0\.1|\[::1\]|localhost)(?::[0-9]{1,5})?", re.I | re.ASCII
)

mcp = create_mcp_server()
register_tasks_tools(mcp)
register_planning_tools(mcp)
register_reviews_tools(mcp)
register_utility_tools(mcp)


class _LocalHTTPMiddleware:
    """Reject browser origins and requests addressed to non-loopback hosts."""

    def __init__(self, app, token: str):
        self.app = app
        self.token = token.encode("ascii")

    def __getattr__(self, name):
        return getattr(self.app, name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Request(scope).headers
        hosts = headers.getlist("host")
        if len(hosts) != 1 or not LOCAL_AUTHORITY.fullmatch(hosts[0]):
            await JSONResponse({"error": "invalid_host"}, 421)(scope, receive, send)
            return
        if "origin" in headers:
            await JSONResponse({"error": "browser_origin_not_allowed"}, 403)(
                scope, receive, send
            )
            return
        if self.token:
            values = headers.getlist("authorization")
            scheme, _, credential = (
                values[0].partition(" ") if len(values) == 1 else ("", "", "")
            )
            if scheme.lower() != "bearer" or not compare_digest(
                credential.encode("latin-1"), self.token
            ):
                await JSONResponse(
                    {"error": "unauthorized"},
                    401,
                    headers={"WWW-Authenticate": 'Bearer realm="Things MCP"'},
                )(scope, receive, send)
                return
        if scope["path"] == "/mcp":
            scope = dict(scope, path="/mcp/")
        await self.app(scope, receive, send)


def _create_combined_app(mcp_instance, transport_mode: str):
    """Create a loopback-only Streamable HTTP application."""
    if transport_mode != "streamable-http":
        raise ValueError("HTTP app requires the streamable-http transport")
    settings = get_settings()
    if settings.things_mcp_host not in LOOPBACK_HOSTS:
        raise ValueError("THINGS_MCP_HOST must be 127.0.0.1, ::1, or localhost")
    token = settings.things_mcp_http_token.get_secret_value()
    if settings.things_mcp_require_auth and not token:
        raise ValueError("THINGS_MCP_REQUIRE_AUTH requires THINGS_MCP_HTTP_TOKEN")
    if token and (
        not re.fullmatch(r"[A-Za-z0-9._~+/=-]{32,}", token)
        or token == settings.things_auth_token
        or token == get_things_auth_token()
    ):
        raise ValueError(
            "Use a separate random THINGS_MCP_HTTP_TOKEN of at least 32 characters"
        )

    http_app = mcp_instance.http_app(
        transport="streamable-http",
        path="/",
        middleware=get_streamable_http_middleware(),
    )

    async def root_redirect(request):
        return RedirectResponse("/mcp/", status_code=307)

    routes = [
        Route("/", root_redirect, methods=["GET", "POST"]),
        Mount("/mcp", app=http_app, name="streamable-http"),
    ]
    return _LocalHTTPMiddleware(
        Starlette(routes=routes, lifespan=http_app.lifespan), token
    )


def run_things_mcp_server(transport: str | None = None):
    """Run the requested transport without probing or starting Things at startup."""
    settings = get_settings()
    transport = transport or settings.things_mcp_transport
    if transport == "stdio":
        mcp.run(
            transport="stdio",
            show_banner=False,
            log_level="INFO" if settings.things_mcp_debug else "WARNING",
        )
        return

    import uvicorn

    uvicorn.run(
        _create_combined_app(mcp, transport),
        host=settings.things_mcp_host,
        port=settings.things_mcp_port,
        ws="none",
        proxy_headers=False,
        access_log=False,
        timeout_graceful_shutdown=5,
    )
