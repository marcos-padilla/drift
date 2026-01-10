"""
Git diff tool for showing file differences.

This module provides a tool for showing differences between git versions,
including working directory changes, staged changes, and commit comparisons.
"""

import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class GitDiffParams(BaseModel):
    """
    Parameters for the git_diff tool.

    Parameters
    ----------
    path : str | None, optional
        Path to git repository (defaults to current directory).
    file : str | None, optional
        Specific file to show diff for.
    staged : bool, default=False
        Show staged changes instead of working directory changes.
    commit1 : str | None, optional
        First commit/tree to compare.
    commit2 : str | None, optional
        Second commit/tree to compare.
    context_lines : int, default=3
        Number of context lines to show around changes.

    Examples
    --------
    >>> params = GitDiffParams(path=".", file="main.py", staged=True)
    """

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current directory)",
    )
    file: str | None = Field(
        None,
        description="Specific file to show diff for",
    )
    staged: bool = Field(
        False,
        description="Show staged changes instead of working directory changes",
    )
    commit1: str | None = Field(
        None,
        description="First commit/tree to compare (e.g., 'HEAD', 'abc123')",
    )
    commit2: str | None = Field(
        None,
        description="Second commit/tree to compare (e.g., 'HEAD~1', 'def456')",
    )
    context_lines: int = Field(
        3,
        ge=0,
        le=100,
        description="Number of context lines to show around changes (default: 3)",
    )


class GitDiffTool(Tool):
    """
    Tool for showing git file differences.

    This tool shows differences between git versions, including working
    directory changes, staged changes, and commit comparisons.

    Attributes
    ----------
    name : str
        Tool name: "git_diff"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[GitDiffParams]
        Parameter schema
    """

    name: str = "git_diff"
    description: str = (
        "Show differences between git versions. Can show working directory "
        "changes, staged changes, or compare specific commits."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[GitDiffParams] = GitDiffParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the git_diff tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing git diff output or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GitDiffParams(**invocation.params)
        repo_path: Path = (
            resolve_path(invocation.cwd, params.path)
            if params.path
            else invocation.cwd
        )

        if not repo_path.exists():
            return ToolResult.error_result(f"Path does not exist: {repo_path}")

        if not repo_path.is_dir():
            return ToolResult.error_result(f"Path is not a directory: {repo_path}")

        # Check if it's a git repository
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return ToolResult.error_result(
                f"Not a git repository: {repo_path}",
            )

        try:
            cmd: list[str] = ["git", "diff"]
            cmd.extend(["-U", str(params.context_lines)])

            if params.staged:
                cmd.append("--staged")
            elif params.commit1:
                if params.commit2:
                    cmd.extend([params.commit1, params.commit2])
                else:
                    cmd.append(params.commit1)

            if params.file:
                file_path = resolve_path(repo_path, params.file)
                if file_path.exists():
                    cmd.append(str(file_path.relative_to(repo_path)))
                else:
                    return ToolResult.error_result(f"File not found: {params.file}")

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return ToolResult.error_result(
                    f"Git diff failed: {result.stderr}",
                    output=result.stdout,
                )

            output: str = result.stdout
            if not output:
                output = "No differences found."

            return ToolResult.success_result(
                output=output,
                metadata={
                    "path": str(repo_path),
                    "file": params.file,
                    "staged": params.staged,
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Git diff command timed out")
        except Exception as e:
            logger.exception(f"Failed to get git diff: {e}")
            return ToolResult.error_result(f"Failed to get git diff: {e}")
