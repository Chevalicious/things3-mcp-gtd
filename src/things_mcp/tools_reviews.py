"""Things 3 reviews tools."""

import logging
import asyncio

import things
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from .tool_annotations import TOOL_ANNOTATIONS

logger = logging.getLogger(__name__)


def _error_result(message: str):
    """Raise a ToolError for standardized MCP error handling."""
    raise ToolError(message)


def register_reviews_tools(mcp: FastMCP):
    """Register review tools with the MCP server."""

    @mcp.tool(
        name="daily-review",
        annotations=TOOL_ANNOTATIONS["daily-review"],
        timeout=5,
        output_schema=None,
    )
    async def daily_review(ctx: Context = None) -> str:
        """Get a daily overview of Today, Inbox, and deadlines.

        Returns:
        - Today's scheduled tasks
        - Overdue tasks
        - Inbox count
        """
        if ctx:
            await ctx.info("Running daily review...")

        try:
            from datetime import date

            today_str = date.today().isoformat()

            # Get data
            today_tasks = things.today()
            inbox_count = things.inbox(count_only=True)

            # Find overdue tasks
            all_todos = things.todos(status="incomplete")
            overdue = [
                t
                for t in all_todos
                if t.get("deadline") and t.get("deadline") < today_str
            ]

            # Build summary
            output = "# Daily Review\n\n"
            output += f"**Summary:** {len(today_tasks or [])} tasks today"
            if overdue:
                output += f", **{len(overdue)} overdue**"
            if inbox_count:
                output += f", {inbox_count} in inbox"
            output += "\n\n"

            # Overdue section (priority)
            if overdue:
                output += "## Overdue\n\n"
                for t in overdue[:5]:
                    output += (
                        f"- **{t.get('title')}** (deadline: {t.get('deadline')})\n"
                    )
                if len(overdue) > 5:
                    output += f"- ...and {len(overdue) - 5} more\n"
                output += "\n"

            # Keep tasks already shown under Overdue out of the second list.
            shown_overdue = {t["uuid"] for t in overdue[:5]}
            today_tasks = [
                t for t in today_tasks or [] if t["uuid"] not in shown_overdue
            ]
            output += "## Today's Tasks\n\n"
            if today_tasks:
                for t in today_tasks:
                    deadline_note = (
                        f" [due: {t.get('deadline')}]" if t.get("deadline") else ""
                    )
                    output += f"- {t.get('title')}{deadline_note}\n"
            else:
                output += "No additional tasks scheduled for today.\n"
            output += "\n"

            return output

        except Exception as e:
            logger.error("Error in daily review (%s)", type(e).__name__)
            _error_result(
                "Error running daily review. Check Things and the server settings."
            )

    @mcp.tool(
        name="weekly-review",
        annotations=TOOL_ANNOTATIONS["weekly-review"],
        timeout=10,
        output_schema=None,
    )
    async def weekly_review(ctx: Context = None) -> str:
        """Summarize open projects, Inbox, and recent activity.

        Returns:
        - Projects with no available to-do
        - Items tagged waiting-for, with overdue follow-ups
        - Someday items
        - Completed this week
        - Inbox status
        """
        if ctx:
            await ctx.info("Running weekly review...")

        try:
            from datetime import date

            today = date.today()
            today_str = today.isoformat()

            output = "# Weekly Review\n\n"

            # 1. Inbox status
            inbox_count = things.inbox(count_only=True)
            if inbox_count:
                output += f"## Inbox: {inbox_count} items\n"
                output += "Use process-inbox to inspect the oldest item.\n\n"
            else:
                output += "## Inbox: Clear\n\n"

            # 2. Stalled projects
            projects = await asyncio.to_thread(things.projects)
            todos = await asyncio.to_thread(things.todos, project=True)
            active_projects = {
                t["project"]
                for t in todos
                if t.get("project")
                and t.get("start") != "Someday"
                and (not t.get("start_date") or t["start_date"] <= today_str)
            }
            stalled = [
                p
                for p in projects
                if p.get("status") == "incomplete"
                and p.get("uuid") not in active_projects
            ]

            if stalled:
                output += f"## Projects Without an Available To-Do: {len(stalled)}\n"
                for p in stalled[:5]:
                    output += f"- **{p.get('title')}**\n"
                if len(stalled) > 5:
                    output += f"- ...and {len(stalled) - 5} more\n"
                output += "\n"
            else:
                output += "## Every Project Has an Available To-Do\n\n"

            # 3. Waiting-for items
            waiting = things.todos(tag="waiting-for", status="incomplete")
            if waiting:
                output += f"## Waiting For: {len(waiting)} items\n\n"
                overdue_waiting = [
                    w
                    for w in waiting
                    if w.get("deadline") and w.get("deadline") < today_str
                ]
                if overdue_waiting:
                    output += "**Overdue follow-ups:**\n"
                    for w in overdue_waiting[:3]:
                        output += f"- {w.get('title')} (was due: {w.get('deadline')})\n"
                    output += "\n"
                output += "Review and follow up on delegated items.\n\n"

            # 4. Someday
            someday = things.someday()
            if someday:
                output += f"## Someday: {len(someday)} items\n"
                output += "\n"
                for s in (someday or [])[:3]:
                    output += f"- {s.get('title')}\n"
                if len(someday or []) > 3:
                    output += f"- ...and {len(someday) - 3} more\n"
                output += "\n"

            # 5. Completed this week
            completed = things.last("7d", status="completed")
            if completed:
                output += f"## Completed This Week: {len(completed)} items\n"
                for c in (completed or [])[:5]:
                    output += f"- ~~{c.get('title')}~~\n"
                if len(completed) > 5:
                    output += f"- ...and {len(completed) - 5} more\n"

            return output

        except Exception as e:
            logger.error("Error in weekly review (%s)", type(e).__name__)
            _error_result(
                "Error running weekly review. Check Things and the server settings."
            )
