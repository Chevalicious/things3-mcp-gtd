"""Command line entry point for Things MCP."""

import argparse
import logging

from pydantic import ValidationError

from .settings import get_settings


def main():
    parser = argparse.ArgumentParser(description="Connect an MCP client to Things 3.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        help="Override THINGS_MCP_TRANSPORT (default: streamable-http).",
    )
    args = parser.parse_args()

    try:
        settings = get_settings()
        logging.basicConfig(
            level=logging.INFO if settings.things_mcp_debug else logging.WARNING
        )
        from .fast_server import run_things_mcp_server

        run_things_mcp_server(args.transport)
    except KeyboardInterrupt:
        pass
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
        parser.exit(2, f"Invalid settings: {fields}\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    main()
