"""
Todo management tool for tracking tasks.

This module provides a tool for managing a task list during a session
with support for adding, completing, listing, and clearing todos.
"""

import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


class TodosParams(BaseModel):
    """
    Parameters for the todos tool.

    Parameters
    ----------
    action : str
        Action: 'add', 'complete', 'list', 'clear'
    id : str | None, optional
        Todo ID (for complete action).
    content : str | None, optional
        Todo content (for add action).

    Examples
    --------
    >>> params = TodosParams(action="add", content="Fix bug in login")
    """

    action: str = Field(..., description="Action: 'add', 'complete', 'list', 'clear'")
    id: str | None = Field(None, description="Todo ID (for complete)")
    content: str | None = Field(None, description="Todo content (for add)")


class TodosTool(Tool):
    """
    Tool for managing a task list during a session.

    This tool provides functionality to track multi-step tasks with
    support for adding, completing, listing, and clearing todos.

    Attributes
    ----------
    name : str
        Tool name: "todos"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: MEMORY
    schema : type[TodosParams]
        Parameter schema
    _todos : dict[str, str]
        Internal storage for todos keyed by ID.
    """

    name: str = "todos"
    description: str = (
        "Manage a task list for the current session. "
        "Use this to track progress on multi-step tasks."
    )
    kind: ToolKind = ToolKind.MEMORY
    schema: type[TodosParams] = TodosParams

    def __init__(self, config) -> None:
        super().__init__(config)
        self._todos: dict[str, str] = {}

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the todos tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters.

        Returns
        -------
        ToolResult
            Result containing todo operation result.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = TodosParams(**invocation.params)

        if params.action.lower() == "add":
            if not params.content:
                return ToolResult.error_result("`content` required for 'add' action")
            todo_id: str = str(uuid.uuid4())[:8]
            self._todos[todo_id] = params.content
            return ToolResult.success_result(
                f"Added todo [{todo_id}]: {params.content}",
            )
        elif params.action.lower() == "complete":
            if not params.id:
                return ToolResult.error_result("`id` required for 'complete' action")
            if params.id not in self._todos:
                return ToolResult.error_result(f"Todo not found: {params.id}")

            content: str = self._todos.pop(params.id)
            return ToolResult.success_result(
                f"Completed todo [{params.id}]: {content}",
            )
        elif params.action == "list":
            if not self._todos:
                return ToolResult.success_result("No todos")
            lines: list[str] = ["Todos:"]

            for todo_id, content in self._todos.items():
                lines.append(f"  [{todo_id}] {content}")
            return ToolResult.success_result("\n".join(lines))
        elif params.action == "clear":
            count: int = len(self._todos)
            self._todos.clear()
            return ToolResult.success_result(f"Cleared {count} todos")
        else:
            return ToolResult.error_result(f"Unknown action: {params.action}")
