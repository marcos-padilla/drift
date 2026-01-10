"""
Write file tool for creating and updating files.

This module provides a tool for writing content to files with support
for creating parent directories and generating file diffs.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import FileDiff, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from core.utils.paths import ensure_parent_directory, resolve_path

logger = logging.getLogger(__name__)


class WriteFileParams(BaseModel):
    """
    Parameters for the write_file tool.

    Parameters
    ----------
    path : str
        Path to the file to write (relative to working directory or absolute).
    content : str
        Content to write to the file.
    create_directories : bool, default=True
        Create parent directories if they don't exist.

    Examples
    --------
    >>> params = WriteFileParams(path="test.py", content="print('hello')")
    """

    path: str = Field(
        ...,
        description="Path to the file to write (relative to working directory or absolute)",
    )
    content: str = Field(..., description="Content to write to the file")
    create_directories: bool = Field(
        True,
        description="Create parent directories if they don't exist",
    )


class WriteFileTool(Tool):
    """
    Tool for writing content to files.

    This tool creates new files or overwrites existing ones, with
    automatic parent directory creation and diff generation.

    Attributes
    ----------
    name : str
        Tool name: "write_file"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[WriteFileParams]
        Parameter schema
    """

    name: str = "write_file"
    description: str = (
        "Write content to a file. Creates the file if it doesn't exist, "
        "or overwrites if it does. Parent directories are created automatically. "
        "Use this for creating new files or completely replacing file contents. "
        "For partial modifications, use the edit tool instead."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[WriteFileParams] = WriteFileParams

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for file write operation.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request with file diff, None if not mutating.
        """
        params = WriteFileParams(**invocation.params)
        path: Path = resolve_path(invocation.cwd, params.path)

        is_new_file: bool = not path.exists()

        old_content: str = ""
        if not is_new_file:
            try:
                old_content = path.read_text(encoding="utf-8")
            except Exception:
                pass

        diff = FileDiff(
            path=path,
            old_content=old_content,
            new_content=params.content,
            is_new_file=is_new_file,
        )

        action: str = "Created" if is_new_file else "Updated"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"{action} file: {path}",
            diff=diff,
            affected_paths=[path],
            is_dangerous=not is_new_file,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the write_file tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing success message and file diff.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success and result.diff:
        ...     print(result.diff.to_diff())
        """
        params = WriteFileParams(**invocation.params)
        path: Path = resolve_path(invocation.cwd, params.path)

        is_new_file: bool = not path.exists()
        old_content: str = ""

        if not is_new_file:
            try:
                old_content = path.read_text(encoding="utf-8")
            except Exception:
                pass

        try:
            if params.create_directories:
                ensure_parent_directory(path)
            elif not path.parent.exists():
                return ToolResult.error_result(
                    f"Parent directory does not exist: {path.parent}",
                )

            path.write_text(params.content, encoding="utf-8")

            action: str = "Created" if is_new_file else "Updated"
            line_count: int = len(params.content.splitlines())

            return ToolResult.success_result(
                f"{action} {path} {line_count} lines",
                diff=FileDiff(
                    path=path,
                    old_content=old_content,
                    new_content=params.content,
                    is_new_file=is_new_file,
                ),
                metadata={
                    "path": str(path),
                    "is_new_file": is_new_file,
                    "lines": line_count,
                    "bytes": len(params.content.encode("utf-8")),
                },
            )
        except OSError as e:
            logger.exception(f"Failed to write file {path}: {e}")
            return ToolResult.error_result(f"Failed to write file: {e}")
