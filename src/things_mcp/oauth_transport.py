"""Opt-in MCP OAuth transport for the owner's GitHub account."""

from urllib.parse import urlsplit

from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.github import GitHubTokenVerifier


class OwnerTokenVerifier(GitHubTokenVerifier):
    def __init__(self, user_id: int):
        super().__init__(required_scopes=["read:user"])
        self.user_id = str(user_id)

    async def verify_token(self, token):
        verified = await super().verify_token(token)
        if verified and verified.claims.get("sub") == self.user_id:
            return verified
        return None


def build_oauth_app(settings, server_factory):
    base_url = settings.things_mcp_oauth_url.rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Set THINGS_MCP_OAUTH_URL to the dedicated HTTPS origin.")
    redirects = [
        uri.strip()
        for uri in settings.things_mcp_oauth_redirect_uris.split(",")
        if uri.strip()
    ]
    for uri in redirects:
        redirect = urlsplit(uri)
        loopback = redirect.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            (
                redirect.scheme != "https"
                and not (loopback and redirect.scheme == "http")
            )
            or not redirect.hostname
            or redirect.username is not None
            or redirect.fragment
            or redirect.query
            or any(char in redirect.path for char in "*?[]")
            or "*" in redirect.netloc
        ):
            raise ValueError("OAuth callbacks must be exact HTTPS or loopback URLs.")

    secret = settings.things_mcp_oauth_github_client_secret.get_secret_value()
    if not (
        secret
        and settings.things_mcp_oauth_github_client_id
        and (settings.things_mcp_oauth_github_user_id or 0) > 0
        and redirects
    ):
        raise ValueError(
            "Configure the GitHub OAuth app, owner account ID, and client callbacks."
        )

    auth = OAuthProxy(
        upstream_authorization_endpoint="https://github.com/login/oauth/authorize",
        upstream_token_endpoint="https://github.com/login/oauth/access_token",
        upstream_client_id=settings.things_mcp_oauth_github_client_id,
        upstream_client_secret=secret,
        token_verifier=OwnerTokenVerifier(settings.things_mcp_oauth_github_user_id),
        base_url=base_url,
        allowed_client_redirect_uris=redirects,
        forward_pkce=False,
        forward_resource=False,
        token_endpoint_auth_method="client_secret_post",
        enable_cimd=False,
    )
    server = server_factory(auth=auth)
    return server.http_app(
        path="/mcp",
        allowed_hosts=[parsed.hostname],
        allowed_origins=[base_url],
    )
