"""Shared tool annotations for Things MCP tools.

This module contains the annotation dictionaries used by all tool modules
to specify tool behavior hints (read-only, destructive, idempotent, etc.).
"""

from typing import Dict
import mcp.types as types

READ_ONLY_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    openWorldHint=False,
)

ADD_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

UPDATE_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    # Several update tools append notes or checklist items.
    idempotentHint=False,
    openWorldHint=False,
)

REPLACE_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)

TOOL_ANNOTATIONS: Dict[str, types.ToolAnnotations] = {
    "get-tasks": READ_ONLY_ANNOTATIONS,
    "focus-mode": READ_ONLY_ANNOTATIONS,
    "complete-task": UPDATE_ANNOTATIONS,
    "capture-task": ADD_ANNOTATIONS,
    "capture-tasks": ADD_ANNOTATIONS,
    "process-inbox": READ_ONLY_ANNOTATIONS,
    "convert-to-project": REPLACE_ANNOTATIONS,
    "schedule-task": ADD_ANNOTATIONS,
    "delegate-task": UPDATE_ANNOTATIONS,
    "defer-task": UPDATE_ANNOTATIONS,
    "plan-project": ADD_ANNOTATIONS,
    "move-task": UPDATE_ANNOTATIONS,
    "modify-task": REPLACE_ANNOTATIONS,
    "daily-review": READ_ONLY_ANNOTATIONS,
    "weekly-review": READ_ONLY_ANNOTATIONS,
    # === Utility Tools ===
    "search-tasks": READ_ONLY_ANNOTATIONS,
    "get-projects": READ_ONLY_ANNOTATIONS,
    "get-areas": READ_ONLY_ANNOTATIONS,
    "get-tags": READ_ONLY_ANNOTATIONS,
    "show-in-app": READ_ONLY_ANNOTATIONS,
    "get-cache-stats": READ_ONLY_ANNOTATIONS,
}
