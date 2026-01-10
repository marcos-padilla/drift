"""
Grep tool for searching text patterns in files.

This module provides a tool for searching regular expression patterns
in file contents with support for case-insensitive matching.
"""

import logging
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import is_binary_file, resolve_path

logger = logging.getLogger(__name__)


class GrepParams(BaseModel):
    """
    Parameters for the grep tool.

    Parameters
    ----------
    pattern : str
        Regular expression pattern to search for.
    path : str, default="."
        File or directory to search in (default: current directory).
    case_insensitive : bool, default=False
        Case-insensitive search (default: false).

    Examples
    --------
    >>> params = GrepParams(pattern="def.*", path="src", case_insensitive=False)
    """

    pattern: str = Field(..., description="Regular expression pattern to search for")
    path: str = Field(
        ".",
        description="File or directory to search in (default: current directory)",
    )
    case_insensitive: bool = Field(
        False,
        description="Case-insensitive search (default: false)",
    )


class GrepTool(Tool):
    """
    Tool for searching regex patterns in files.

    This tool searches for regular expression patterns in file contents,
    supporting both single files and directory trees.

    Attributes
    ----------
    name : str
        Tool name: "grep"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[GrepParams]
        Parameter schema
    """

    name: str = "grep"
    description: str = (
        "Search for a regex pattern in file contents. "
        "Returns matching lines with file paths and line numbers."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[GrepParams] = GrepParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the grep tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing matching lines with file paths.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GrepParams(**invocation.params)

        search_path: Path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists():
            return ToolResult.error_result(f"Path does not exist: {search_path}")

        try:
            flags: int = re.IGNORECASE if params.case_insensitive else 0
            pattern = re.compile(params.pattern, flags)
        except re.error as e:
            return ToolResult.error_result(f"Invalid regex pattern: {e}")

        if search_path.is_dir():
            files: list[Path] = self._find_files(search_path)
        else:
            files = [search_path]

        output_lines: list[str] = []
        matches: int = 0

        for file_path in files:
            try:
                content: str = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.debug(f"Failed to read {file_path}: {e}")
                continue

            lines: list[str] = content.splitlines()
            file_matches: bool = False

            for i, line in enumerate(lines, start=1):
                if pattern.search(line):
                    matches += 1
                    if not file_matches:
                        try:
                            rel_path: Path = file_path.relative_to(invocation.cwd)
                            output_lines.append(f"=== {rel_path} ===")
                        except ValueError:
                            output_lines.append(f"=== {file_path} ===")
                        file_matches = True

                    output_lines.append(f"{i}:{line}")

            if file_matches:
                output_lines.append("")

        if not output_lines:
            return ToolResult.success_result(
                f"No matches found for pattern '{params.pattern}'",
                metadata={
                    "path": str(search_path),
                    "matches": 0,
                    "files_searched": len(files),
                },
            )

        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "path": str(search_path),
                "matches": matches,
                "files_searched": len(files),
            },
        )

    def _find_files(self, search_path: Path) -> list[Path]:
        """
        Find all text files in a directory tree.

        Parameters
        ----------
        search_path : Path
            Directory to search.

        Returns
        -------
        list[Path]
            List of text file paths found.
        """
        files: list[Path] = []

        for root, dirs, filenames in os.walk(search_path):
            dirs[:] = [
                d
                for d in dirs
                if d not in {"node_modules", "__pycache__", ".git", ".venv", "venv"}
            ]

            for filename in filenames:
                if filename.startswith("."):
                    continue

                file_path: Path = Path(root) / filename
                if not is_binary_file(file_path):
                    files.append(file_path)
                    if len(files) >= 500:
                        return files

        return files
