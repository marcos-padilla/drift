"""
Data models for the hook system.

This module defines models for hook-related data structures.
"""

from typing import Any

from pydantic import BaseModel, Field

from core.config.schema import HookTrigger
from core.tools.models import ToolResult


class HookExecutionContext(BaseModel):
    """
    Context information passed to hook execution.

    Parameters
    ----------
    trigger : HookTrigger
        Trigger that caused this hook execution.
    tool_name : str | None, optional
        Name of the tool if this is a tool-related hook.
    tool_params : dict[str, Any] | None, optional
        Tool parameters if applicable.
    tool_result : ToolResult | None, optional
        Tool result if this is an after_tool hook.
    user_message : str | None, optional
        User message if this is an agent-related hook.
    agent_response : str | None, optional
        Agent response if this is an after_agent hook.
    error : Exception | None, optional
        Error if this is an on_error hook.

    Examples
    --------
    >>> context = HookExecutionContext(
    ...     trigger=HookTrigger.BEFORE_TOOL,
    ...     tool_name="write_file"
    ... )
    """

    trigger: HookTrigger = Field(description="Hook trigger type")
    tool_name: str | None = Field(default=None, description="Tool name")
    tool_params: dict[str, Any] | None = Field(
        default=None,
        description="Tool parameters",
    )
    tool_result: ToolResult | None = Field(
        default=None,
        description="Tool result",
    )
    user_message: str | None = Field(default=None, description="User message")
    agent_response: str | None = Field(default=None, description="Agent response")
    error: str | None = Field(default=None, description="Error message")
