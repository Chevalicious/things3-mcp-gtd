"""
Things MCP Server - Model Context Protocol server for Things task management app.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("things3-mcp-gtd")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0+unknown"
