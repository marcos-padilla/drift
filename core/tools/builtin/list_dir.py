"""
List directory tool for exploring directory contents.

This module provides a tool for listing files and directories with
support for hidden file filtering.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class ListDirParams(BaseModel):
    """
    Parameters for the list_dir tool.

    Parameters
    ----------
    path : str, default="."
        Directory path to list (default: current directory).
    include_hidden : bool, default=False
        Whether to include hidden files and directories (default: false).

    Examples
    --------
    >>> params = ListDirParams(path="src", include_hidden=False)
    """

    path: str = Field(
        ".",
        description="Directory path to list (default: current directory)",
    )
    include_hidden: bool = Field(
        False,
        description="Whether to include hidden files and directories (default: false)",
    )


class ListDirTool(Tool):
    """
    Tool for listing directory contents.

    This tool lists files and directories in a specified path with
    support for filtering hidden files.

    Attributes
    ----------
    name : str
        Tool name: "list_dir"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[ListDirParams]
        Parameter schema
    """

    name: str = "list_dir"
    description: str = "List contents of a directory"
    kind: ToolKind = ToolKind.READ
    schema: type[ListDirParams] = ListDirParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the list_dir tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing directory listing.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = ListDirParams(**invocation.params)

        dir_path: Path = resolve_path(invocation.cwd, params.path)

        if not dir_path.exists() or not dir_path.is_dir():
            return ToolResult.error_result(f"Directory does not exist: {dir_path}")

        try:
            items = sorted(
                dir_path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except Exception as e:
            logger.exception(f"Error listing directory {dir_path}: {e}")
            return ToolResult.error_result(f"Error listing directory: {e}")

        if not params.include_hidden:
            items = [item for item in items if not item.name.startswith(".")]

        if not items:
            return ToolResult.success_result(
                "Directory is empty",
                metadata={"path": str(dir_path), "entries": 0},
            )

        lines: list[str] = []

        for item in items:
            if item.is_dir():
                lines.append(f"{item.name}/")
            else:
                lines.append(item.name)

        return ToolResult.success_result(
            "\n".join(lines),
            metadata={
                "path": str(dir_path),
                "entries": len(items),
            },
        )
