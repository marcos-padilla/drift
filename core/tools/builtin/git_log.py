"""
Git log tool for viewing commit history.

This module provides a tool for viewing git commit history with filtering
by author, date, path, and other options.
"""

import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class GitLogParams(BaseModel):
    """
    Parameters for the git_log tool.

    Parameters
    ----------
    path : str | None, optional
        Path to git repository (defaults to current directory).
    limit : int, default=20
        Maximum number of commits to show (1-100).
    author : str | None, optional
        Filter commits by author (name or email pattern).
    since : str | None, optional
        Show commits since date (e.g., "2024-01-01", "2 weeks ago").
    until : str | None, optional
        Show commits until date.
    file_path : str | None, optional
        Show commits affecting a specific file or directory.
    oneline : bool, default=False
        Show one line per commit.

    Examples
    --------
    >>> params = GitLogParams(path=".", limit=10, author="John", oneline=True)
    """

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current directory)",
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of commits to show (default: 20)",
    )
    author: str | None = Field(
        None,
        description="Filter commits by author (name or email pattern)",
    )
    since: str | None = Field(
        None,
        description="Show commits since date (e.g., '2024-01-01', '2 weeks ago')",
    )
    until: str | None = Field(
        None,
        description="Show commits until date",
    )
    file_path: str | None = Field(
        None,
        description="Show commits affecting a specific file or directory",
    )
    oneline: bool = Field(
        False,
        description="Show one line per commit",
    )


class GitLogTool(Tool):
    """
    Tool for viewing git commit history.

    This tool shows commit history with filtering options by author,
    date, path, and other criteria.

    Attributes
    ----------
    name : str
        Tool name: "git_log"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[GitLogParams]
        Parameter schema
    """

    name: str = "git_log"
    description: str = (
        "View git commit history. Can filter by author, date, path, "
        "and show various formats of commit information."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[GitLogParams] = GitLogParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the git_log tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
               -------
        ToolResult
            Result containing git log output or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GitLogParams(**invocation.params)
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
            cmd: list[str] = ["git", "log"]
            cmd.extend(["-n", str(params.limit)])

            if params.oneline:
                cmd.append("--oneline")
            else:
                cmd.append("--pretty=format:%h - %an, %ar : %s")

            if params.author:
                cmd.extend(["--author", params.author])

            if params.since:
                cmd.extend(["--since", params.since])

            if params.until:
                cmd.extend(["--until", params.until])

            if params.file_path:
                file_path = resolve_path(repo_path, params.file_path)
                if file_path.exists():
                    cmd.append("--")
                    cmd.append(str(file_path.relative_to(repo_path)))
                else:
                    return ToolResult.error_result(
                        f"File or directory not found: {params.file_path}",
                    )

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return ToolResult.error_result(
                    f"Git log failed: {result.stderr}",
                    output=result.stdout,
                )

            output: str = result.stdout
            if not output:
                output = "No commits found matching the criteria."

            return ToolResult.success_result(
                output=output,
                metadata={
                    "path": str(repo_path),
                    "limit": params.limit,
                    "count": len(output.splitlines()),
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Git log command timed out")
        except Exception as e:
            logger.exception(f"Failed to get git log: {e}")
            return ToolResult.error_result(f"Failed to get git log: {e}")
