"""Things 3 tasks tools."""

import logging
import asyncio
from typing import Optional, List, Union

import things
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from .batch_capture import CaptureRows, capture_batch
from .formatters import format_todo
from .utils import _normalize_id
from .url_scheme import (
    add_todo,
    update_todo,
    execute_url,
    add_project_with_tasks,
)
from .cache import invalidate_caches_for
from .tag_handler import prepare_tags
from .tool_annotations import TOOL_ANNOTATIONS
from .write_confirmation import create_and_observe, creation_result, observe

logger = logging.getLogger(__name__)


def _error_result(message: str):
    """Raise a ToolError for standardized MCP error handling."""
    raise ToolError(message)


def _matching_projects(title: str) -> set[str]:
    return {
        p["uuid"]
        for p in things.projects(search_query=title, status=None)
        if p.get("title") == title and p.get("uuid")
    }


def register_tasks_tools(mcp: FastMCP):
    """Register task tools with the MCP server."""

    @mcp.tool(
        name="get-tasks",
        annotations=TOOL_ANNOTATIONS["get-tasks"],
        timeout=5,
        output_schema=None,
    )
    async def get_tasks(
        view: Optional[str] = None,
        context: Optional[Union[str, List[str]]] = None,
        energy: Optional[str] = None,
        time_available: Optional[str] = None,
        area: Optional[str] = None,
        project: Optional[str] = None,
        include_completed: bool = False,
        include_details: bool = False,
        ctx: Context = None,
    ) -> str:
        """List to-dos from a Things view, optionally filtered by tag, area, or project.

        The three tag filters each match an existing Things tag exactly, and a
        task must satisfy every filter given.

        Args:
            view: inbox, today, tomorrow, upcoming, anytime, someday, logbook, trash, or deadlines. Omit for all open to-dos.
            context: Tag name, or a list of tag names (matches any of them)
            energy: A second tag name the task must also have
            time_available: A third tag name the task must also have
            area: Filter by area name or UUID
            project: Filter by project name or UUID
            include_completed: Include completed tasks (default False)
            include_details: Include notes, checklist items, and tags

        Examples:
            get_tasks(view="today")
            get_tasks(view="anytime", context="Errands")
            get_tasks(context="waiting-for")
        """
        if ctx:
            await ctx.info("Fetching tasks...")

        try:
            status = None if include_completed else "incomplete"
            # Build query based on view
            if view == "inbox":
                todos = await asyncio.to_thread(things.inbox, status=status)
            elif view == "today":
                todos = await asyncio.to_thread(things.today, status=status)
            elif view == "tomorrow":
                # Things doesn't have a direct tomorrow() function
                todos = await asyncio.to_thread(things.upcoming, status=status)
                # Filter to tomorrow only
                from datetime import date, timedelta

                tomorrow = (date.today() + timedelta(days=1)).isoformat()
                todos = [t for t in todos if t.get("start_date") == tomorrow]
            elif view == "upcoming":
                todos = await asyncio.to_thread(things.upcoming, status=status)
            elif view == "anytime":
                todos = await asyncio.to_thread(things.anytime, status=status)
            elif view == "someday":
                todos = await asyncio.to_thread(things.someday, status=status)
            elif view == "logbook":
                todos = (
                    await asyncio.to_thread(things.logbook)
                    if hasattr(things, "logbook")
                    else await asyncio.to_thread(things.last, "7d", status="completed")
                )
            elif view == "trash":
                todos = await asyncio.to_thread(things.trash, status=status)
            elif view == "deadlines":
                # Get tasks with deadlines
                todos = await asyncio.to_thread(
                    things.todos, deadline=True, status=status
                )
            elif view is None:
                todos = await asyncio.to_thread(things.todos, status=status)
            else:
                _error_result(
                    f"Unknown view '{view}'. Valid views: inbox, today, tomorrow, upcoming, anytime, someday, logbook, trash, deadlines"
                )

            if not todos:
                todos = []

            # Filter by context (tag)
            if context:
                context_tags = [context] if isinstance(context, str) else context
                todos = [
                    t
                    for t in todos
                    if any(tag in (t.get("tags") or []) for tag in context_tags)
                ]

            # Filter by energy tag
            if energy:
                todos = [t for t in todos if energy in (t.get("tags") or [])]

            # Filter by time available tag
            if time_available:
                todos = [t for t in todos if time_available in (t.get("tags") or [])]

            # Filter by area
            if area:
                todos = [
                    t
                    for t in todos
                    if t.get("area") == area or t.get("area_title") == area
                ]

            # Filter by project
            if project:
                todos = [
                    t
                    for t in todos
                    if t.get("project") == project or t.get("project_title") == project
                ]

            # Filter completed unless requested
            if not include_completed and view not in ("logbook",):
                todos = [t for t in todos if t.get("status") != "completed"]

            if not todos:
                filters = []
                if view:
                    filters.append(f"view={view}")
                if context:
                    filters.append("context")
                if energy:
                    filters.append("energy")
                filter_str = ", ".join(filters) if filters else "no filters"
                return f"No tasks found ({filter_str}). Try different filters or add tasks with capture-task."

            # Format output with summary
            summary = f"**{len(todos)} task{'s' if len(todos) != 1 else ''}**"
            if view:
                summary += f" in {view}"
            if context:
                summary += " matching the context filter"
            summary += "\n\n"

            formatted_todos = [format_todo(todo, include_details) for todo in todos]
            return summary + "\n\n---\n\n".join(formatted_todos)

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error in get-tasks (%s)", type(e).__name__)
            _error_result("Error fetching tasks. Check Things and the server settings.")

    @mcp.tool(
        name="focus-mode",
        annotations=TOOL_ANNOTATIONS["focus-mode"],
        timeout=5,
        output_schema=None,
    )
    async def focus_mode(
        context: Optional[str] = None,
        energy: Optional[str] = None,
        time_available: Optional[str] = None,
        include_details: bool = False,
        ctx: Context = None,
    ) -> str:
        """Get the single most important task to work on right now.

        Use when: asking "what should I do next?"

        Priority order:
        1. Overdue tasks with deadline (oldest first)
        2. Today's tasks with deadline (earliest deadline first)
        3. Today's tasks without deadline
        4. Anytime tasks

        Args:
            context: Existing tag the task must have
            energy: A second tag the task must also have
            time_available: A third tag the task must also have
            include_details: Include notes, checklist items, and tags
        """
        if ctx:
            await ctx.info("Finding your most important task...")

        try:
            from datetime import date

            today_str = date.today().isoformat()
            selected_task = None
            selection_reason = ""

            # 1. Check for overdue tasks with deadlines
            all_todos = things.todos(status="incomplete")
            overdue = [
                t
                for t in all_todos
                if t.get("deadline") and t.get("deadline") < today_str
            ]

            # Apply context/energy/time filters
            def matches_filters(task):
                if context and context not in (task.get("tags") or []):
                    return False
                if energy and energy not in (task.get("tags") or []):
                    return False
                if time_available and time_available not in (task.get("tags") or []):
                    return False
                return True

            overdue = [t for t in overdue if matches_filters(t)]
            if overdue:
                selected_task = sorted(overdue, key=lambda t: t.get("deadline", ""))[0]
                selection_reason = (
                    f"OVERDUE (deadline was {selected_task.get('deadline')})"
                )

            # 2. Check today's tasks with deadlines
            if not selected_task:
                today_tasks = things.today()
                today_with_deadline = [
                    t
                    for t in today_tasks
                    if t.get("deadline") == today_str and matches_filters(t)
                ]
                if today_with_deadline:
                    selected_task = today_with_deadline[0]
                    selection_reason = "Due TODAY with deadline"

            # 3. Check today's tasks without deadlines
            if not selected_task:
                today_tasks = things.today()
                today_no_deadline = [
                    t
                    for t in today_tasks
                    if not t.get("deadline") and matches_filters(t)
                ]
                if today_no_deadline:
                    selected_task = today_no_deadline[0]
                    selection_reason = "Scheduled for today"

            # 4. Check anytime tasks
            if not selected_task:
                anytime_tasks = things.anytime()
                anytime_filtered = [t for t in anytime_tasks if matches_filters(t)]
                if anytime_filtered:
                    selected_task = anytime_filtered[0]
                    selection_reason = "Next available action"

            if not selected_task:
                filter_desc = []
                if context:
                    filter_desc.append("context")
                if energy:
                    filter_desc.append("energy")
                if time_available:
                    filter_desc.append("time available")

                filter_str = (
                    ", ".join(filter_desc) if filter_desc else "current filters"
                )
                return (
                    f"No tasks match {filter_str}.\n\n"
                    "Try:\n"
                    "- Removing a tag filter\n"
                    "- Checking that tasks carry the tags you filter by\n"
                    "- Use get-tasks(view='anytime') to see all available tasks"
                )

            # Format the focused task with context
            output = f"**FOCUS: {selection_reason}**\n\n"
            return output + format_todo(selected_task, include_details)

        except Exception as e:
            logger.error("Error in focus-mode (%s)", type(e).__name__)
            _error_result(
                "Error finding focus task. Check Things and the server settings."
            )

    @mcp.tool(
        name="complete-task", annotations=TOOL_ANNOTATIONS["complete-task"], timeout=30
    )
    async def complete_task(
        task_id: Optional[str] = None,
        task_title: Optional[str] = None,
        completion_notes: Optional[str] = None,
        ctx: Context = None,
    ) -> str:
        """Mark a task as complete.

        Use when: Finishing a task. Provide task_id if known, or task_title to search.

        Args:
            task_id: UUID of the task to complete (preferred if known)
            task_title: Title to search for (fuzzy match). If multiple match, returns list.
            completion_notes: Optional notes to append before completing
        """
        if ctx:
            await ctx.info("Completing task...")

        # Normalize null-like values
        task_id = _normalize_id(task_id)

        if not task_id and not task_title:
            return "Please provide a task_id or task_title to identify the task."

        try:
            # If title provided, search for matching task
            if task_title and not task_id:
                matches = things.todos(status="incomplete")
                matches = [
                    t
                    for t in matches
                    if task_title.lower() in t.get("title", "").lower()
                ]

                if len(matches) == 0:
                    return (
                        f"No task found matching '{task_title}'.\n\n"
                        "Use search-tasks to find the correct task, or check "
                        "get-tasks(view='logbook') if already completed."
                    )

                if len(matches) > 1:
                    result = f"Found {len(matches)} tasks matching '{task_title}'. Please specify:\n\n"
                    for t in matches[:5]:
                        result += f"- **{t.get('title')}** (ID: `{t.get('uuid')}`)\n"
                    if len(matches) > 5:
                        result += f"\n...and {len(matches) - 5} more."
                    return result

                task_id = matches[0].get("uuid")

            url = update_todo(
                id=task_id,
                completed=True,
                append_notes=f"\n[Completed] {completion_notes}"
                if completion_notes
                else None,
            )
            success = await asyncio.to_thread(execute_url, url)

            if not success:
                _error_result("Failed to complete task")

            # Invalidate caches
            invalidate_caches_for(
                ["get-tasks", "get-today", "get-inbox", "get-anytime"]
            )

            def completed():
                task = things.get(task_id) or {}
                return task.get("status") == "completed" and (
                    not completion_notes
                    or f"[Completed] {completion_notes}" in (task.get("notes") or "")
                )

            if await asyncio.to_thread(observe, completed):
                return f"Task completed. ID: `{task_id}`"
            return f"Completion request submitted for `{task_id}`. Check Things before retrying."

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error completing task (%s)", type(e).__name__)
            _error_result(
                "Error completing task. Check Things and the server settings."
            )

    @mcp.tool(
        name="capture-task", annotations=TOOL_ANNOTATIONS["capture-task"], timeout=30
    )
    async def capture_task(
        title: str,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        ctx: Context = None,
    ) -> str:
        """Add a to-do to the Inbox.

        Instead use: schedule-task if you already know when/where it belongs.

        Args:
            title: What needs to be done (required)
            notes: Additional details (optional)
            tags: Existing Things tag names (optional)
        """
        if ctx:
            await ctx.info("Capturing to inbox: …")

        try:
            # Ensure tags exist
            if tags:
                await asyncio.to_thread(prepare_tags, tags)

            # Create in inbox (no when/list specified = inbox)
            url = add_todo(title=title, notes=notes, tags=tags)
            item_id = await asyncio.to_thread(
                create_and_observe,
                execute_url,
                url,
                lambda: things.inbox(search_query=title, status=None),
                title,
                lambda item: not notes or item.get("notes") == notes,
            )
            invalidate_caches_for(["get-inbox", "get-tasks"])
            return creation_result("Task captured", title, item_id)

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error capturing task (%s)", type(e).__name__)
            _error_result("Error capturing task. Check Things and the server settings.")

    @mcp.tool(
        name="capture-tasks",
        annotations=TOOL_ANNOTATIONS["capture-tasks"],
        timeout=30,
        output_schema=None,
    )
    async def capture_tasks(tasks: CaptureRows = None) -> str:
        """Capture up to 10 Inbox to-dos in one Things request.

        Each row has a title and optional notes or existing tags. Every row
        must pass preflight. After sending, check Things before retrying any
        unconfirmed row.
        """
        return await asyncio.to_thread(capture_batch, tasks)

    @mcp.tool(
        name="process-inbox",
        annotations=TOOL_ANNOTATIONS["process-inbox"],
        timeout=5,
        output_schema=None,
    )
    async def process_inbox(include_details: bool = False, ctx: Context = None) -> str:
        """Show the oldest inbox item and suggest ways to organize it.

        This tool only reads the inbox. Use the item's ID with another tool to make changes.

        Args:
            include_details: Include notes, checklist items, and tags
        """
        if ctx:
            await ctx.info("Processing inbox...")

        try:
            inbox_items = things.inbox()

            if not inbox_items:
                return (
                    "**Inbox is empty.**\n\n"
                    "Your inbox is empty. Use capture-task when new items come up."
                )

            item = min(inbox_items, key=lambda task: task.get("created") or "9999")
            remaining = len(inbox_items) - 1

            output = f"**Processing Inbox** ({remaining} item{'s' if remaining != 1 else ''} remaining)\n\n"
            output += format_todo(item, include_details)
            output += "\n\n---\n\n"
            output += (
                "Use modify-task to edit or reschedule this item. "
                "Use defer-task to move it to Someday, or convert-to-project "
                "if it needs several steps."
            )

            return output

        except Exception as e:
            logger.error("Error processing inbox (%s)", type(e).__name__)
            _error_result(
                "Error processing inbox. Check Things and the server settings."
            )

    @mcp.tool(
        name="convert-to-project",
        annotations=TOOL_ANNOTATIONS["convert-to-project"],
        timeout=30,
    )
    async def convert_to_project(
        task_id: str,
        first_action: Optional[str] = None,
        ctx: Context = None,
    ) -> str:
        """Convert a task into a project when it requires multiple steps.

        Preserves from the original task:
        - Title becomes project title
        - Notes, tags, and area are transferred
        - Deadline becomes project deadline (not on child tasks)
        - Incomplete checklist items become project tasks

        Args:
            task_id: UUID of the task to convert
            first_action: Title of a first to-do (added before checklist items)
        """
        if ctx:
            await ctx.info("Converting task to project...")

        # Normalize null-like values
        task_id = _normalize_id(task_id)

        if not task_id:
            return "Please provide a task_id (the UUID of the task to convert to a project)."

        try:
            # Get the original task
            task = things.get(task_id)
            if not task:
                _error_result(f"Task not found: {task_id}")

            if task.get("type") != "to-do":
                _error_result("Can only convert to-do items to projects")

            # Create project with task's details
            project_title = task.get("title", "New Project")
            project_notes = task.get("notes", "")
            project_deadline = task.get("deadline")

            # Get checklist items from the original task
            checklist_items = things.checklist_items(task_id)

            # Build tasks array for the project
            tasks = []
            if first_action:
                tasks.append({"title": first_action, "when": "anytime"})

            # Convert checklist items to project tasks (incomplete ones only)
            for item in checklist_items:
                if item.get("status") != "completed":
                    tasks.append({"title": item.get("title", ""), "when": "anytime"})

            # Require the token before any creation. Do not cancel the source
            # unless the new project can be distinguished from existing ones.
            cancel_url = update_todo(id=task_id, canceled=True)
            before = await asyncio.to_thread(_matching_projects, project_title)
            url = add_project_with_tasks(
                title=project_title,
                tasks=tasks,
                notes=project_notes,
                deadline=project_deadline,
                tags=task.get("tags"),
                area=task.get("area_title"),
            )
            success = await asyncio.to_thread(execute_url, url)

            if not success:
                _error_result("Failed to create project")

            new_projects = set()
            for _ in range(12):
                new_projects = (
                    await asyncio.to_thread(_matching_projects, project_title)
                ) - before
                if new_projects:
                    break
                await asyncio.sleep(0.25)
            if len(new_projects) != 1:
                _error_result(
                    "Could not confirm the new project. The original task was left unchanged. Check Things before retrying."
                )
            if not await asyncio.to_thread(execute_url, cancel_url):
                _error_result(
                    "Project created, but cancellation could not be confirmed. Check Things before retrying."
                )

            invalidate_caches_for(["get-inbox", "get-projects", "get-tasks"])

            # Build result message
            result = f"Created project '{project_title}' (ID: `{next(iter(new_projects))}`). Cancellation of the original task was submitted."
            if project_deadline:
                result += f"\nDeadline: {project_deadline}"

            checklist_count = len(
                [i for i in checklist_items if i.get("status") != "completed"]
            )
            if first_action and checklist_count > 0:
                result += f"\nTasks: {first_action} + {checklist_count} from checklist"
            elif first_action:
                result += f"\nFirst action: {first_action}"
            elif checklist_count > 0:
                result += f"\nConverted {checklist_count} checklist items to tasks."
            else:
                result += "\n\n**Warning:** The project has no tasks yet. Use schedule-task to add one."

            return result

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error converting to project (%s)", type(e).__name__)
            _error_result(
                "Error converting to project. Check Things and the server settings."
            )
