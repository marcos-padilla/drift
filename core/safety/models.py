"""
Data models for safety and approval management.

This module defines models for representing approval contexts and decisions.
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    """
    Decision types for tool call approvals.

    Attributes
    ----------
    APPROVED : str
        The action is approved and can proceed.
    REJECTED : str
        The action is rejected and should not proceed.
    NEEDS_CONFIRMATION : str
        The action requires user confirmation before proceeding.

    Examples
    --------
    >>> decision = ApprovalDecision.APPROVED
    >>> if decision == ApprovalDecision.NEEDS_CONFIRMATION:
    ...     # Request user confirmation
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CONFIRMATION = "needs_confirmation"


class ApprovalContext(BaseModel):
    """
    Context information for approval decisions.

    This model contains all information needed to make an approval
    decision for a tool call or command execution.

    Parameters
    ----------
    tool_name : str
        Name of the tool being called.
    params : dict[str, Any]
        Parameters passed to the tool.
    is_mutating : bool
        Whether the action modifies system state.
    affected_paths : list[Path]
        List of file paths that will be affected by this action.
    command : str | None, optional
        Shell command if this is a command execution.
    is_dangerous : bool, default=False
        Whether the action is flagged as potentially dangerous.

    Examples
    --------
    >>> context = ApprovalContext(
    ...     tool_name="write_file",
    ...     params={"path": "test.py", "content": "print('hello')"},
    ...     is_mutating=True,
    ...     affected_paths=[Path("test.py")]
    ... )
    """

    tool_name: str = Field(description="Name of the tool")
    params: dict[str, Any] = Field(description="Tool parameters")
    is_mutating: bool = Field(description="Whether action modifies state")
    affected_paths: list[Path] = Field(
        default_factory=list,
        description="Paths affected by this action",
    )
    command: str | None = Field(default=None, description="Shell command if applicable")
    is_dangerous: bool = Field(
        default=False,
        description="Whether action is potentially dangerous",
    )


class ToolConfirmation(BaseModel):
    """
    Confirmation request for a tool call.

    This model represents a request for user confirmation before
    executing a potentially risky tool call.

    Parameters
    ----------
    tool_name : str
        Name of the tool requesting confirmation.
    description : str
        Human-readable description of what the tool will do.
    context : ApprovalContext
        Full approval context for this tool call.

    Examples
    --------
    >>> confirmation = ToolConfirmation(
    ...     tool_name="write_file",
    ...     description="Write file test.py",
    ...     context=approval_context
    ... )
    """

    tool_name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of the action")
    context: ApprovalContext = Field(description="Approval context")
