"""
Git status tool for checking repository status.

This module provides a tool for checking git repository status including
modified files, staged changes, untracked files, and branch information.
"""

import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class GitStatusParams(BaseModel):
    """
    Parameters for the git_status tool.

    Parameters
    ----------
    path : str | None, optional
        Path to git repository (defaults to current directory).
    short : bool, default=False
        Use short format output.

    Examples
    --------
    >>> params = GitStatusParams(path=".", short=True)
    """

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current directory)",
    )
    short: bool = Field(
        False,
        description="Use short format output",
    )


class GitStatusTool(Tool):
    """
    Tool for checking git repository status.

    This tool shows the status of a git repository including modified,
    staged, and untracked files, as well as branch information.

    Attributes
    ----------
    name : str
        Tool name: "git_status"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[GitStatusParams]
        Parameter schema
    """

    name: str = "git_status"
    description: str = (
        "Check the status of a git repository. Shows modified, staged, "
        "and untracked files, branch information, and ahead/behind status."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[GitStatusParams] = GitStatusParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the git_status tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing git status output or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GitStatusParams(**invocation.params)
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
            cmd: list[str] = ["git", "status"]
            if params.short:
                cmd.append("--short")

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return ToolResult.error_result(
                    f"Git status failed: {result.stderr}",
                    output=result.stdout,
                )

            # Get branch information
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            branch: str = (
                branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            )

            # Get ahead/behind status
            ahead_behind = ""
            if branch != "unknown":
                tracking_result = subprocess.run(
                    ["git", "rev-list", "--left-right", "@{u}..HEAD", "--count"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if tracking_result.returncode == 0:
                    counts = tracking_result.stdout.strip().split()
                    if len(counts) == 2:
                        ahead, behind = counts
                        if ahead != "0" or behind != "0":
                            ahead_behind = f" (ahead {ahead}, behind {behind})"

            output: str = result.stdout
            if branch != "unknown":
                output = f"Branch: {branch}{ahead_behind}\n\n{output}"

            return ToolResult.success_result(
                output=output,
                metadata={
                    "branch": branch,
                    "path": str(repo_path),
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Git status command timed out")
        except Exception as e:
            logger.exception(f"Failed to get git status: {e}")
            return ToolResult.error_result(f"Failed to get git status: {e}")
