"""
Protocol definitions for tool extensibility.

This module defines protocols that allow for flexible tool implementations
and testing through dependency injection.
"""

from typing import Any, Protocol
from pathlib import Path

from core.tools.models import ToolInvocation, ToolResult


class ToolProtocol(Protocol):
    """
    Protocol for tool implementations.

    This protocol defines the interface that all tools must implement,
    allowing for different tool types to be used interchangeably.

    Attributes
    ----------
    name : str
        Unique name of the tool.
    description : str
        Human-readable description of what the tool does.
    kind : ToolKind
        Category of the tool operation.
    """

    name: str
    description: str
    kind: Any  # ToolKind enum

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the tool with the given invocation.

        Parameters
        ----------
        invocation : ToolInvocation
            Invocation context with parameters and working directory.

        Returns
        -------
        ToolResult
            Result of the tool execution.

        Raises
        ------
        Exception
            Various exceptions may be raised depending on the implementation.
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Validate tool parameters.

        Parameters
        ----------
        params : dict[str, Any]
            Parameters to validate.

        Returns
        -------
        list[str]
            List of validation error messages. Empty list if valid.
        """
        ...

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """
        Check if the tool operation modifies system state.

        Parameters
        ----------
        params : dict[str, Any]
            Tool parameters.

        Returns
        -------
        bool
            True if the operation is mutating.
        """
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.

        Returns
        -------
        dict[str, Any]
            OpenAI-compatible function schema.
        """
        ...
