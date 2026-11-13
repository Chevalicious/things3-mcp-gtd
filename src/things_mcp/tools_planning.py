"""Things 3 planning tools."""

import logging
import asyncio
from typing import Optional, List, Dict, Any

import things
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from .utils import _normalize_id
from .url_scheme import (
    add_todo,
    build_when_with_reminder,
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


def _resolve_destination(task_id, list_name, list_id, heading, heading_id):
    """Resolve legacy destination inputs without guessing between duplicate names."""
    if list_name and not list_id:
        matches = [
            item["uuid"]
            for item in [*things.projects(), *things.areas()]
            if list_name.casefold()
            in (item["title"].casefold(), item["uuid"].casefold())
        ]
        if len(matches) != 1:
            _error_result("Destination is missing or ambiguous. Use its ID.")
        list_id = matches[0]
    if not (heading or heading_id):
        if list_id:
            target = things.get(list_id) or {}
            if (
                target.get("type") not in {"area", "project"}
                or target.get("trashed")
                or (
                    target["type"] == "project" and target.get("status") != "incomplete"
                )
            ):
                _error_result("Destination ID must identify an area or active project.")
        return list_id, None
    if heading_id:
        target = things.get(heading_id) or {}
        project_id = target.get("project")
        if target.get("type") != "heading" or not project_id:
            _error_result("Heading ID does not identify an active project heading.")
        if list_id and project_id != list_id:
            _error_result("Heading belongs to a different project.")
        list_id = project_id
    if not list_id:
        task = (things.get(task_id) or {}) if task_id else {}
        list_id = task.get("project")
        if not list_id and (current_heading := task.get("heading")):
            list_id = (things.get(current_heading) or {}).get("project")
    project = things.get(list_id) if list_id else None
    if (
        not project
        or project.get("type") != "project"
        or project.get("trashed")
        or project.get("status") != "incomplete"
    ):
        _error_result("An existing project is required for a heading.")
    headings = things.tasks(project=list_id, type="heading")
    matches = [
        item
        for item in headings
        if (
            item["uuid"] == heading_id
            if heading_id
            else item["title"].casefold() == heading.casefold()
        )
    ]
    if len(matches) != 1:
        _error_result("Heading is missing or ambiguous. Use its ID.")
    return list_id, matches[0]


def register_planning_tools(mcp: FastMCP):
    """Register scheduling and editing tools."""

    @mcp.tool(
        name="schedule-task", annotations=TOOL_ANNOTATIONS["schedule-task"], timeout=30
    )
    async def schedule_task(
        title: str,
        when: Optional[str] = None,
        deadline: Optional[str] = None,
        project: Optional[str] = None,
        area: Optional[str] = None,
        context: Optional[List[str]] = None,
        checklist: Optional[List[str]] = None,
        notes: Optional[str] = None,
        heading: Optional[str] = None,
        reminder_time: Optional[str] = None,
        reminder_at: Optional[str] = None,
        ctx: Context = None,
    ) -> str:
        """Create a task with specific scheduling and organization.

        Use when: You know when/where this task belongs.
        Instead use: capture-task for quick capture without organizing.

        Args:
            title: What needs to be done
            when: Things schedule, e.g. tomorrow, tomorrow@09:00, anytime, or YYYY-MM-DD
            deadline: Hard deadline (YYYY-MM-DD)
            project: Project name or UUID to add to
            area: Area name or UUID
            context: Existing Things tag names to apply
            checklist: Subtasks/checklist items
            notes: Additional notes
            heading: Existing heading within the destination project
            reminder_time: Time such as 6pm on a dated when value
            reminder_at: Full date and time, such as tomorrow@18:00
        """
        if ctx:
            await ctx.info("Scheduling task for …")

        if not title:
            return "Please provide a title for the task."
        if not when and not reminder_at:
            return "Please provide a when value (e.g., 'today', 'tomorrow', 'anytime', or YYYY-MM-DD)."

        try:
            when = build_when_with_reminder(when, reminder_time, reminder_at)
            if project and area:
                _error_result("Choose either a project or an area.")
            destination = None
            if requested := project or area:
                lists = await asyncio.to_thread(
                    things.projects if project else things.areas
                )
                exact_ids = [
                    item["uuid"] for item in lists if item.get("uuid") == requested
                ]
                titles = [
                    item["uuid"]
                    for item in lists
                    if item.get("uuid")
                    and item.get("title", "").casefold() == requested.casefold()
                ]
                matches = exact_ids or titles
                if len(matches) != 1:
                    _error_result(
                        "Destination was not found or is ambiguous. Use its UUID from get-projects or get-areas."
                    )
                destination = matches[0]

            heading_item = None
            if heading:
                destination, heading_item = await asyncio.to_thread(
                    _resolve_destination, None, None, destination, heading, None
                )

            # Combine context with any other tags
            tags = context if context else None
            if tags:
                await asyncio.to_thread(prepare_tags, tags)

            # Build URL
            url = add_todo(
                title=title,
                notes=notes,
                when=when,
                deadline=deadline,
                tags=tags,
                checklist_items=checklist,
                list_id=destination,
                heading=heading_item["title"] if heading_item else None,
            )

            item_id = await asyncio.to_thread(
                create_and_observe,
                execute_url,
                url,
                lambda: things.todos(search_query=title, status=None),
                title,
                lambda item: (
                    (not notes or item.get("notes") == notes)
                    and (
                        not destination
                        or heading_item
                        or item.get("project" if project else "area") == destination
                    )
                    and (
                        not heading_item or item.get("heading") == heading_item["uuid"]
                    )
                ),
            )

            invalidate_caches_for(
                ["get-tasks", "get-today", "get-upcoming", "get-anytime"]
            )

            result = creation_result("Task created", title, item_id) + "\n"
            result += f"- Requested schedule: {when}\n"
            if deadline:
                result += f"- Requested deadline: {deadline}\n"
            if project:
                result += f"- Project: {project}\n"
            if area:
                result += f"- Area: {area}\n"
            if context:
                result += f"- Context: {', '.join(context)}\n"

            return result

        except ValueError as exc:
            _error_result(str(exc))
        except ToolError:
            raise
        except Exception as e:
            logger.error("Error scheduling task (%s)", type(e).__name__)
            _error_result(
                "Error scheduling task. Check Things and the server settings."
            )

    @mcp.tool(
        name="delegate-task", annotations=TOOL_ANNOTATIONS["delegate-task"], timeout=30
    )
    async def delegate_task(
        task_id: str,
        delegated_to: str,
        follow_up_date: Optional[str] = None,
        notes: Optional[str] = None,
        ctx: Context = None,
    ) -> str:
        """Mark a task as handed off to someone else.

        This adds the 'waiting-for' tag, updates the title to show who you're
        waiting on, and sets an optional follow-up deadline.

        Args:
            task_id: UUID of the task to delegate
            delegated_to: Person's name you're waiting on
            follow_up_date: When to follow up (YYYY-MM-DD)
            notes: Notes about the delegation (e.g., "Emailed on Jan 20")
        """
        if ctx:
            await ctx.info("Delegating task to …")

        # Normalize null-like values
        task_id = _normalize_id(task_id)

        if not task_id:
            return "Please provide a task_id (the UUID of the task to delegate)."
        if not delegated_to:
            return "Please provide whom you're delegating to (delegated_to)."

        try:
            # Get the original task
            task = things.get(task_id)
            if not task:
                _error_result(f"Task not found: {task_id}")

            original_title = task.get("title", "")
            new_title = f"Waiting: {delegated_to} - {original_title}"

            # Build delegation note
            from datetime import date

            delegation_note = f"\n[Delegated {date.today().isoformat()}]"
            if notes:
                delegation_note += f" {notes}"

            # Ensure waiting-for tag exists
            await asyncio.to_thread(prepare_tags, ["waiting-for"])

            # Update the task
            url = update_todo(
                id=task_id,
                title=new_title,
                append_notes=delegation_note,
                add_tags=["waiting-for"],
                deadline=follow_up_date,
            )

            success = await asyncio.to_thread(execute_url, url)
            if not success:
                _error_result("Failed to delegate task")

            invalidate_caches_for(["get-tasks"])

            result = f"Delegation request submitted for {original_title} (waiting for {delegated_to}).\n"
            result += "- Requested tag: waiting-for\n"
            if follow_up_date:
                result += f"- Follow up: {follow_up_date}\n"
            else:
                result += "- No follow-up date set. Will appear in weekly review.\n"

            return result

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error delegating task (%s)", type(e).__name__)
            _error_result(
                "Error delegating task. Check Things and the server settings."
            )

    @mcp.tool(name="defer-task", annotations=TOOL_ANNOTATIONS["defer-task"], timeout=30)
    async def defer_task(
        task_id: str,
        defer_to: str,
        reason: Optional[str] = None,
        ctx: Context = None,
    ) -> str:
        """Reschedule a task to a date or move it to Someday.

        Args:
            task_id: UUID of the task to defer
            defer_to: When - "someday", "tomorrow", "next_week", or YYYY-MM-DD
            reason: Why you're deferring (appended to notes)
        """
        if ctx:
            await ctx.info("Deferring task to …")

        # Normalize null-like values
        task_id = _normalize_id(task_id)

        if not task_id:
            return "Please provide a task_id (the UUID of the task to defer)."
        if not defer_to:
            return "Please provide when to defer to (defer_to: 'someday', 'tomorrow', or YYYY-MM-DD)."

        try:
            # Map friendly names to Things values
            when_map = {
                "someday": "someday",
                "tomorrow": "tomorrow",
                "next_week": None,  # Calculate date
            }

            when_value = when_map.get(defer_to, defer_to)

            # Handle next_week specially
            if defer_to == "next_week":
                from datetime import date, timedelta

                next_monday = date.today() + timedelta(
                    days=(7 - date.today().weekday())
                )
                when_value = next_monday.isoformat()

            # Build notes update
            notes_update = None
            if reason:
                from datetime import date

                notes_update = f"\n[Deferred {date.today().isoformat()}] {reason}"

            # Update the task
            url = update_todo(
                id=task_id,
                when=when_value,
                append_notes=notes_update,
            )

            success = await asyncio.to_thread(execute_url, url)
            if not success:
                _error_result("Failed to defer task")

            invalidate_caches_for(
                ["get-tasks", "get-today", "get-upcoming", "get-someday"]
            )

            if defer_to == "someday":
                return (
                    "Move to Someday submitted.\n\n"
                    "This item will appear in your weekly review for reconsideration."
                )
            else:
                return f"Reschedule to {when_value} submitted to Things."

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error deferring task (%s)", type(e).__name__)
            _error_result("Error deferring task. Check Things and the server settings.")

    @mcp.tool(
        name="plan-project", annotations=TOOL_ANNOTATIONS["plan-project"], timeout=30
    )
    async def plan_project(
        title: str,
        tasks: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None,
        when: Optional[str] = None,
        deadline: Optional[str] = None,
        area: Optional[str] = None,
        headings: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        ctx: Context = None,
    ) -> str:
        """Submit a project and its initial tasks in one request.

        Args:
            title: Project title
            tasks: List of task objects - each with 'title' and optional 'when', 'notes', 'tags'
            notes: Project notes
            when: Project schedule
            deadline: Project deadline
            area: Area name to add to
            headings: Existing request format mapping new heading names to their tasks

        Example tasks:
            [
                {"title": "Research options", "when": "anytime"},
                {"title": "Draft proposal", "when": "anytime"},
                {"title": "Review with team"}
            ]
        """
        if ctx:
            await ctx.info("Creating project: …")

        try:
            tasks = tasks or []
            headings = headings or {}
            all_tasks = [
                *tasks,
                *(task for group in headings.values() for task in group),
            ]
            if (
                not title.strip()
                or any(not name.strip() for name in headings)
                or any(
                    not isinstance(task.get("title"), str) or not task["title"].strip()
                    for task in all_tasks
                )
            ):
                _error_result("Provide a title for the project and each task.")

            # Use the Things JSON command for project and task creation.
            url = add_project_with_tasks(
                title=title,
                tasks=tasks,
                notes=notes,
                when=when,
                deadline=deadline,
                area=area,
                headings=headings,
            )

            item_id = await asyncio.to_thread(
                create_and_observe,
                execute_url,
                url,
                lambda: things.projects(search_query=title, status=None),
                title,
                lambda item: not notes or item.get("notes") == notes,
            )

            invalidate_caches_for(["get-projects", "get-tasks"])

            result = creation_result("Project created", title, item_id) + "\n"
            result += f"- {len(all_tasks)} tasks requested\n"
            if deadline:
                result += f"- Deadline: {deadline}\n"

            return result

        except ToolError:
            raise
        except Exception as e:
            logger.error("Error creating project (%s)", type(e).__name__)
            _error_result(
                "Error creating project. Check Things and the server settings."
            )

    async def move_task(task_id: str, destination_id: str) -> str:
        """Move an existing to-do to a project, area, or heading by ID.

        Use get-projects(include_items=true) for headings and get-areas for areas.
        Requires THINGS_AUTH_TOKEN. Returns the existing task ID after confirming
        its destination. Does not create or duplicate a task.

        Args:
            task_id: ID of the existing to-do
            destination_id: ID of the destination project, area, or heading
        """

        def move():
            source = things.get(task_id)
            if not source or source.get("type") != "to-do" or source.get("trashed"):
                _error_result("Task ID does not identify a to-do outside the Trash.")
            destination = things.get(destination_id) or {}
            kind = destination.get("type")
            heading_id = destination_id if kind == "heading" else None
            list_id = destination.get("project") if heading_id else destination_id
            project = things.get(list_id) if heading_id and list_id else None
            if (
                kind not in {"area", "project", "heading"}
                or destination.get("trashed")
                or (kind != "area" and destination.get("status") != "incomplete")
                or (
                    heading_id
                    and (
                        not project
                        or project.get("type") != "project"
                        or project.get("trashed")
                        or project.get("status") != "incomplete"
                    )
                )
            ):
                _error_result(
                    "Destination ID must identify an area, active project, or active heading."
                )

            def is_at_destination(item):
                if not item or item.get("trashed"):
                    return False
                if heading_id:
                    return item.get("heading") == heading_id
                if kind == "project":
                    return item.get("project") == list_id and not item.get("heading")
                return item.get("area") == list_id and not (
                    item.get("project") or item.get("heading")
                )

            if is_at_destination(source):
                return f"Task is already at the requested destination. ID: `{task_id}`"

            if not execute_url(
                update_todo(id=task_id, list_id=list_id, heading_id=heading_id)
            ):
                _error_result(
                    "Could not confirm delivery of the move. Check Things before retrying."
                )
            invalidate_caches_for(
                ["get-tasks", "get-inbox", "get-projects", "get-areas"]
            )
            if not observe(lambda: is_at_destination(things.get(task_id))):
                _error_result(
                    "Move was submitted but the destination was not confirmed. Check Things before retrying."
                )
            return f"Moved task to {destination['title']}. ID: `{task_id}`"

        try:
            if not _normalize_id(task_id) or not _normalize_id(destination_id):
                _error_result("Provide both a task ID and a destination ID.")
            return await asyncio.to_thread(move)
        except ToolError:
            raise
        except Exception as e:
            logger.error("Error moving task (%s)", type(e).__name__)
            _error_result("Could not verify the move. Check Things before retrying.")

    mcp.tool(name="move-task", annotations=TOOL_ANNOTATIONS["move-task"], timeout=15)(
        move_task
    )

    @mcp.tool(
        name="organize-task", annotations=TOOL_ANNOTATIONS["organize-task"], timeout=20
    )
    async def organize_task(
        task_id: str,
        project: Optional[str] = None,
        project_id: Optional[str] = None,
        area: Optional[str] = None,
        heading: Optional[str] = None,
        heading_id: Optional[str] = None,
    ) -> str:
        """Move a task to a project, area, or existing heading by name or ID."""
        if area and (project or project_id):
            _error_result("Choose either a project or an area.")
        list_id, target = await asyncio.to_thread(
            _resolve_destination,
            task_id,
            project or area,
            project_id,
            heading,
            heading_id,
        )
        return await move_task(task_id, target["uuid"] if target else list_id)

    @mcp.tool(
        name="modify-task", annotations=TOOL_ANNOTATIONS["modify-task"], timeout=30
    )
    async def modify_task(
        task_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        add_notes: Optional[str] = None,
        when: Optional[str] = None,
        deadline: Optional[str] = None,
        tags: Optional[List[str]] = None,
        add_tags: Optional[List[str]] = None,
        checklist: Optional[List[str]] = None,
        add_checklist: Optional[List[str]] = None,
        project: Optional[str] = None,
        project_id: Optional[str] = None,
        heading: Optional[str] = None,
        heading_id: Optional[str] = None,
        reminder_time: Optional[str] = None,
        reminder_at: Optional[str] = None,
        ctx: Context = None,
    ) -> str:
        """General task modification for updates not covered by specific tools.

        Instead use: complete-task for completing, defer-task for rescheduling,
                     delegate-task for delegation.

        Args:
            task_id: UUID of the task to update
            title: New title (replaces existing)
            notes: New notes (replaces existing)
            add_notes: Notes to append (preserves existing)
            when: New schedule
            deadline: New deadline
            tags: New tags (replaces existing)
            add_tags: Tags to add (preserves existing)
            checklist: New checklist items (replaces existing)
            add_checklist: Checklist items to append (preserves existing)
            project: Destination project or area name
            project_id: Destination project or area ID
            heading: Existing heading in the destination or current project
            heading_id: Existing heading ID
            reminder_time: Time such as 6pm on a dated when value
            reminder_at: Full date and time, such as tomorrow@18:00
        """
        if ctx:
            await ctx.info("Updating task...")

        # Normalize null-like values
        task_id = _normalize_id(task_id)

        if not task_id:
            return "Please provide a task_id (the UUID of the task to update)."

        try:
            when = build_when_with_reminder(when, reminder_time, reminder_at)
            list_id, target = await asyncio.to_thread(
                _resolve_destination, task_id, project, project_id, heading, heading_id
            )
            # Ensure tags exist
            all_tags = (tags or []) + (add_tags or [])
            if all_tags:
                await asyncio.to_thread(prepare_tags, all_tags)

            # Build URL
            url = update_todo(
                id=task_id,
                title=title,
                notes=notes,
                append_notes=add_notes,
                when=when,
                deadline=deadline,
                tags=tags,
                add_tags=add_tags,
                checklist_items=checklist,
                append_checklist_items=add_checklist,
                list_id=list_id,
                heading_id=target["uuid"] if target else None,
            )

            success = await asyncio.to_thread(execute_url, url)
            if not success:
                _error_result("Failed to update task")

            invalidate_caches_for(["get-tasks"])

            return "Update request submitted to Things. Check the task to verify the change."

        except ValueError as exc:
            _error_result(str(exc))
        except ToolError:
            raise
        except Exception as e:
            logger.error("Error updating task (%s)", type(e).__name__)
            _error_result("Error updating task. Check Things and the server settings.")
