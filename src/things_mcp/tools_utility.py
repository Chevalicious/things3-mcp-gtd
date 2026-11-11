"""Utility Tools: search, list projects/areas/tags, show in app, cache stats."""

import logging
from typing import Optional

import things
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from .formatters import format_todo, format_project, format_area, format_tag
import asyncio

from .url_scheme import show, execute_url
from .cache import get_cache_stats
from .tool_annotations import TOOL_ANNOTATIONS

logger = logging.getLogger(__name__)


def _error_result(message: str):
    """Raise a ToolError for standardized MCP error handling."""
    raise ToolError(message)


def register_utility_tools(mcp: FastMCP):
    """Register utility tools with the MCP server."""

    @mcp.tool(
        name="search-tasks",
        annotations=TOOL_ANNOTATIONS["search-tasks"],
        timeout=5,
        output_schema=None,
    )
    async def search_tasks(
        query: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        area: Optional[str] = None,
        deadline: Optional[str] = None,
        include_details: bool = False,
        ctx: Context = None,
    ) -> str:
        """Search for tasks by keyword or filters.

        Use when: Looking for a specific task or filtering by criteria.

        Args:
            query: Search text (matches title and notes)
            status: Filter by status - incomplete, completed, canceled
            tag: Filter by tag (context)
            area: Filter by area UUID
            deadline: Filter by deadline date
            include_details: Include notes, checklist items, and tags
        """
        if ctx:
            await ctx.info("Searching tasks...")

        try:
            # Build search parameters
            kwargs = {}
            if status:
                kwargs["status"] = status
            if tag:
                kwargs["tag"] = tag
            if area:
                kwargs["area"] = area
            if deadline:
                kwargs["deadline"] = deadline

            if not query and not kwargs:
                _error_result(
                    "Provide query or at least one filter (status, tag, area, deadline)"
                )
            if query:
                # Preserve the existing search across item types while applying filters.
                todos = await asyncio.to_thread(things.search, query, **kwargs)
            else:
                todos = await asyncio.to_thread(things.todos, **kwargs)

            if not todos:
                return "No tasks found matching your criteria."

            # Format results
            summary = f"**Found {len(todos)} task{'s' if len(todos) != 1 else ''}**\n\n"
            formatted_todos = [
                format_todo(todo, include_details) for todo in todos[:20]
            ]

            result = summary + "\n\n---\n\n".join(formatted_todos)
            if len(todos) > 20:
                result += f"\n\n*...and {len(todos) - 20} more results*"

            return result

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error searching tasks (%s)", type(e).__name__)
            _error_result(
                "Error searching tasks. Check Things and the server settings."
            )

    @mcp.tool(
        name="get-projects",
        annotations=TOOL_ANNOTATIONS["get-projects"],
        timeout=5,
        output_schema=None,
    )
    async def get_projects(include_items: bool = False, ctx: Context = None) -> str:
        """Get all projects from Things.

        Args:
            include_items: Include tasks and heading IDs within projects
        """
        if ctx:
            await ctx.info("Fetching projects...")
        projects = things.projects()

        if not projects:
            return "No projects found"

        formatted_projects = [
            format_project(project, include_items) for project in projects
        ]
        return "\n\n---\n\n".join(formatted_projects)

    @mcp.tool(
        name="get-areas",
        annotations=TOOL_ANNOTATIONS["get-areas"],
        timeout=5,
        output_schema=None,
    )
    async def get_areas(include_items: bool = False, ctx: Context = None) -> str:
        """Get all areas from Things.

        Args:
            include_items: Include projects and tasks within areas
        """
        if ctx:
            await ctx.info("Fetching areas...")
        areas = things.areas()

        if not areas:
            return "No areas found"

        formatted_areas = [format_area(area, include_items) for area in areas]
        return "\n\n---\n\n".join(formatted_areas)

    @mcp.tool(
        name="get-tags",
        annotations=TOOL_ANNOTATIONS["get-tags"],
        timeout=5,
        output_schema=None,
    )
    async def get_tags(include_items: bool = False, ctx: Context = None) -> str:
        """Get all tags.

        Args:
            include_items: Include items tagged with each tag
        """
        if ctx:
            await ctx.info("Fetching tags...")
        tags = things.tags()

        if not tags:
            return "No tags found"

        formatted_tags = [format_tag(tag, include_items) for tag in tags]
        return "\n\n---\n\n".join(formatted_tags)

    @mcp.tool(
        name="show-in-app", annotations=TOOL_ANNOTATIONS["show-in-app"], timeout=10
    )
    async def show_in_app(
        id: str,
        ctx: Context = None,
    ) -> str:
        """Open a specific item or list in the Things app.

        Args:
            id: Item UUID, or list name: inbox, today, upcoming, anytime, someday, logbook,
                tomorrow, deadlines, repeating, all-projects, logged-projects
        """
        if ctx:
            await ctx.info("Opening '…")

        if not id:
            return "Please provide an id (item UUID or list name: inbox, today, upcoming, anytime, someday, etc.)."

        try:
            url = show(id=id)
            if not url:
                _error_result(f"Failed to construct URL for '{id}'")
            result = await asyncio.to_thread(execute_url, url)
            if not result:
                _error_result(f"Failed to open '{id}'")

            return f"Opened '{id}' in Things"

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error showing in app (%s)", type(e).__name__)
            _error_result("Error showing in app. Check Things and the server settings.")

    @mcp.tool(
        name="get-cache-stats",
        annotations=TOOL_ANNOTATIONS["get-cache-stats"],
        timeout=5,
    )
    async def get_cache_statistics(ctx: Context = None) -> str:
        """Get cache performance statistics."""
        if ctx:
            await ctx.info("Fetching cache statistics...")
        stats = get_cache_stats()

        return f"""Cache Statistics:
- Total entries: {stats["entries"]}
- Cache hits: {stats["hits"]}
- Cache misses: {stats["misses"]}
- Hit rate: {stats["hit_rate"]}
- Total requests: {stats["total_requests"]}"""
