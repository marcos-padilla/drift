"""
Data models for subagent definitions.

This module defines models for configuring subagents with specific
goals, allowed tools, and execution limits.
"""

from pydantic import BaseModel, Field


class SubagentDefinition(BaseModel):
    """
    Definition for a subagent configuration.

    Parameters
    ----------
    name : str
        Unique name for the subagent.
    description : str
        Human-readable description of what the subagent does.
    goal_prompt : str
        Prompt template describing the subagent's goal and behavior.
    allowed_tools : list[str] | None, optional
        List of tool names the subagent is allowed to use.
        If None, all tools are allowed.
    max_turns : int, default=20
        Maximum number of conversation turns for the subagent.
    timeout_seconds : float, default=600.0
        Maximum execution time in seconds.

    Examples
    --------
    >>> definition = SubagentDefinition(
    ...     name="codebase_investigator",
    ...     description="Investigates codebase structure",
    ...     goal_prompt="You are a codebase investigation specialist...",
    ...     allowed_tools=["read_file", "grep"]
    ... )
    """

    name: str = Field(description="Subagent name")
    description: str = Field(description="Subagent description")
    goal_prompt: str = Field(description="Goal prompt template")
    allowed_tools: list[str] | None = Field(
        default=None,
        description="Allowed tool names (None = all tools)",
    )
    max_turns: int = Field(
        default=20,
        ge=1,
        description="Maximum conversation turns",
    )
    timeout_seconds: float = Field(
        default=600.0,
        ge=1.0,
        description="Maximum execution time in seconds",
    )
