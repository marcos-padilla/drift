"""
Data models for the tools system.

This module defines Pydantic models for tool-related data structures
including tool results, invocations, and file diffs.
"""

import difflib
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ToolKind(str, Enum):
    """
    Categories of tools based on their operation type.

    Attributes
    ----------
    READ : str
        Read-only operations (e.g., reading files, listing directories).
    WRITE : str
        Write operations (e.g., writing files, creating directories).
    SHELL : str
        Shell command execution.
    NETWORK : str
        Network operations (e.g., web requests).
    MEMORY : str
        Memory/storage operations.
    MCP : str
        Model Context Protocol tools.

    Examples
    --------
    >>> kind = ToolKind.READ
    >>> if kind == ToolKind.WRITE:
    ...     # Requires approval
    """

    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    NETWORK = "network"
    MEMORY = "memory"
    MCP = "mcp"


class FileDiff(BaseModel):
    """
    Represents a diff between two file versions.

    Parameters
    ----------
    path : Path
        Path to the file being diffed.
    old_content : str
        Original file content.
    new_content : str
        New file content.
    is_new_file : bool, default=False
        Whether this is a new file (old_content is empty).
    is_deletion : bool, default=False
        Whether this is a file deletion (new_content is empty).

    Examples
    --------
    >>> diff = FileDiff(
    ...     path=Path("test.py"),
    ...     old_content="print('old')",
    ...     new_content="print('new')"
    ... )
    >>> diff_str = diff.to_diff()
    """

    path: Path = Field(description="File path")
    old_content: str = Field(description="Original content")
    new_content: str = Field(description="New content")
    is_new_file: bool = Field(default=False, description="Is new file")
    is_deletion: bool = Field(default=False, description="Is deletion")

    def to_diff(self) -> str:
        """
        Generate a unified diff string.

        Returns
        -------
        str
            Unified diff format string.

        Examples
        --------
        >>> diff = FileDiff(path=Path("test.py"), old_content="old", new_content="new")
        >>> diff_str = diff.to_diff()
        """
        old_lines: list[str] = self.old_content.splitlines(keepends=True)
        new_lines: list[str] = self.new_content.splitlines(keepends=True)

        if old_lines and not old_lines[-1].endswith("\n"):
            old_lines[-1] += "\n"
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"

        old_name: str = "/dev/null" if self.is_new_file else str(self.path)
        new_name: str = "/dev/null" if self.is_deletion else str(self.path)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_name,
            tofile=new_name,
        )

        return "".join(diff)


class ToolResult(BaseModel):
    """
    Result of a tool execution.

    Parameters
    ----------
    success : bool
        Whether the tool execution was successful.
    output : str
        Output from the tool execution.
    error : str | None, optional
        Error message if execution failed.
    metadata : dict[str, Any], default={}
        Additional metadata about the execution.
    truncated : bool, default=False
        Whether the output was truncated.
    diff : FileDiff | None, optional
        File diff if this was a file modification.
    exit_code : int | None, optional
        Exit code for shell commands.

    Examples
    --------
    >>> result = ToolResult.success_result("File read successfully")
    >>> result = ToolResult.error_result("File not found")
    """

    success: bool = Field(description="Whether execution succeeded")
    output: str = Field(default="", description="Tool output")
    error: str | None = Field(default=None, description="Error message")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    truncated: bool = Field(default=False, description="Output was truncated")
    diff: FileDiff | None = Field(default=None, description="File diff")
    exit_code: int | None = Field(default=None, description="Exit code")

    @classmethod
    def error_result(
        cls,
        error: str,
        output: str = "",
        **kwargs: Any,
    ) -> "ToolResult":
        """
        Create an error result.

        Parameters
        ----------
        error : str
            Error message.
        output : str, default=""
            Optional output text.
        **kwargs : Any
            Additional fields for the result.

        Returns
        -------
        ToolResult
            Error result instance.

        Examples
        --------
        >>> result = ToolResult.error_result("File not found")
        """
        return cls(
            success=False,
            output=output,
            error=error,
            **kwargs,
        )

    @classmethod
    def success_result(cls, output: str, **kwargs: Any) -> "ToolResult":
        """
        Create a success result.

        Parameters
        ----------
        output : str
            Output text.
        **kwargs : Any
            Additional fields for the result.

        Returns
        -------
        ToolResult
            Success result instance.

        Examples
        --------
        >>> result = ToolResult.success_result("Operation completed")
        """
        return cls(
            success=True,
            output=output,
            error=None,
            **kwargs,
        )

    def to_model_output(self) -> str:
        """
        Convert result to format expected by LLM.

        Returns
        -------
        str
            Formatted output string.

        Examples
        --------
        >>> result = ToolResult.success_result("Done")
        >>> output = result.to_model_output()
        """
        if self.success:
            return self.output

        return f"Error: {self.error}\n\nOutput:\n{self.output}"


class ToolInvocation(BaseModel):
    """
    Represents an invocation of a tool.

    Parameters
    ----------
    params : dict[str, Any]
        Parameters for the tool.
    cwd : Path
        Current working directory for the invocation.

    Examples
    --------
    >>> invocation = ToolInvocation(
    ...     params={"path": "test.py"},
    ...     cwd=Path.cwd()
    ... )
    """

    params: dict[str, Any] = Field(description="Tool parameters")
    cwd: Path = Field(description="Current working directory")


class ToolConfirmation(BaseModel):
    """
    Confirmation request for a tool call.

    This is used by the safety system to request user approval
    for potentially risky operations.

    Parameters
    ----------
    tool_name : str
        Name of the tool requesting confirmation.
    params : dict[str, Any]
        Parameters for the tool call.
    description : str
        Human-readable description of the action.
    diff : FileDiff | None, optional
        File diff if this is a file modification.
    affected_paths : list[Path], default=[]
        List of file paths that will be affected.
    command : str | None, optional
        Shell command if this is a command execution.
    is_dangerous : bool, default=False
        Whether the action is flagged as dangerous.

    Examples
    --------
    >>> confirmation = ToolConfirmation(
    ...     tool_name="write_file",
    ...     params={"path": "test.py"},
    ...     description="Write file test.py"
    ... )
    """

    tool_name: str = Field(description="Tool name")
    params: dict[str, Any] = Field(description="Tool parameters")
    description: str = Field(description="Action description")
    diff: FileDiff | None = Field(default=None, description="File diff")
    affected_paths: list[Path] = Field(
        default_factory=list,
        description="Affected file paths",
    )
    command: str | None = Field(default=None, description="Shell command")
    is_dangerous: bool = Field(default=False, description="Is dangerous action")
