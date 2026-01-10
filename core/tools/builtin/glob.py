"""
Glob tool for finding files by pattern.

This module provides a tool for finding files matching glob patterns
with support for recursive matching.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class GlobParams(BaseModel):
    """
    Parameters for the glob tool.

    Parameters
    ----------
    pattern : str
        Glob pattern to match.
    path : str, default="."
        Directory to search in (default: current directory).

    Examples
    --------
    >>> params = GlobParams(pattern="*.py", path="src")
    """

    pattern: str = Field(..., description="Glob pattern to match")
    path: str = Field(
        ".",
        description="Directory to search in (default: current directory)",
    )


class GlobTool(Tool):
    """
    Tool for finding files by glob pattern.

    This tool searches for files matching glob patterns with support
    for recursive matching using **.

    Attributes
    ----------
    name : str
        Tool name: "glob"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[GlobParams]
        Parameter schema
    """

    name: str = "glob"
    description: str = (
        "Find files matching a glob pattern. Supports ** for recursive matching."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[GlobParams] = GlobParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the glob tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing matching file paths.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GlobParams(**invocation.params)

        search_path: Path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists() or not search_path.is_dir():
            return ToolResult.error_result(f"Directory does not exist: {search_path}")

        try:
            matches: list[Path] = list(search_path.glob(params.pattern))
            matches = [p for p in matches if p.is_file()]
        except Exception as e:
            logger.exception(f"Error searching with glob pattern: {e}")
            return ToolResult.error_result(f"Error searching: {e}")

        output_lines: list[str] = []

        for file_path in matches[:1000]:
            try:
                rel_path: Path = file_path.relative_to(invocation.cwd)
            except ValueError:
                rel_path = file_path

            output_lines.append(str(rel_path))

        if len(matches) > 1000:
            output_lines.append("...(limited to 1000 results)")

        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "path": str(search_path),
                "matches": len(matches),
            },
        )
