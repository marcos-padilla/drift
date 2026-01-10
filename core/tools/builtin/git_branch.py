"""
Git branch tool for branch operations.

This module provides a tool for listing, creating, deleting, and switching
git branches.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class GitBranchParams(BaseModel):
    """
    Parameters for the git_branch tool.

    Parameters
    ----------
    path : str | None, optional
        Path to git repository (defaults to current directory).
    action : str
        Action to perform: "list", "create", "delete", "switch", or "show".
    branch_name : str | None, optional
        Branch name (required for create, delete, switch).
    force : bool, default=False
        Force operation (for delete or switch with uncommitted changes).

    Examples
    --------
    >>> params = GitBranchParams(path=".", action="list")
    >>> params = GitBranchParams(path=".", action="create", branch_name="feature/new")
    """

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current directory)",
    )
    action: str = Field(
        ...,
        description="Action: 'list', 'create', 'delete', 'switch', or 'show'",
    )
    branch_name: str | None = Field(
        None,
        description="Branch name (required for create, delete, switch)",
    )
    force: bool = Field(
        False,
        description="Force operation (for delete or switch)",
    )


class GitBranchTool(Tool):
    """
    Tool for git branch operations.

    This tool can list, create, delete, and switch branches with
    appropriate safety checks.

    Attributes
    ----------
    name : str
        Tool name: "git_branch"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE (for mutating operations)
    schema : type[GitBranchParams]
        Parameter schema
    """

    name: str = "git_branch"
    description: str = (
        "Perform git branch operations: list branches, create new branches, "
        "delete branches, switch branches, or show current branch information."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[GitBranchParams] = GitBranchParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """
        Check if this operation modifies git state.

        Parameters
        ----------
        params : dict[str, Any]
            Tool parameters.

        Returns
        -------
        bool
            True for create, delete, switch; False for list, show.
        """
        action: str = params.get("action", "")
        return action in {"create", "delete", "switch"}

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for branch operations.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request if operation needs approval.
        """
        params = GitBranchParams(**invocation.params)
        action: str = params.action

        if action not in {"create", "delete", "switch"}:
            return None

        is_dangerous: bool = action == "delete"
        description: str = f"{action.capitalize()} branch"
        if params.branch_name:
            description += f": {params.branch_name}"

        if action == "delete":
            description += "\n⚠️  This will delete the branch permanently"
        elif action == "switch":
            description += "\n⚠️  This will switch branches (uncommitted changes may be lost)"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=description,
            is_dangerous=is_dangerous,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the git_branch tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing branch operation output or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GitBranchParams(**invocation.params)
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

        action: str = params.action.lower()

        try:
            if action == "list":
                result = subprocess.run(
                    ["git", "branch", "-a"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Git branch list failed: {result.stderr}",
                        output=result.stdout,
                    )

                # Get current branch
                current_result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                current: str = (
                    current_result.stdout.strip()
                    if current_result.returncode == 0
                    else "unknown"
                )

                output: str = f"Current branch: {current}\n\n{result.stdout}"
                return ToolResult.success_result(
                    output=output,
                    metadata={"current_branch": current},
                )

            elif action == "create":
                if not params.branch_name:
                    return ToolResult.error_result(
                        "Branch name is required for create action",
                    )

                result = subprocess.run(
                    ["git", "branch", params.branch_name],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to create branch: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output=f"Branch '{params.branch_name}' created successfully",
                    metadata={"branch_name": params.branch_name},
                )

            elif action == "delete":
                if not params.branch_name:
                    return ToolResult.error_result(
                        "Branch name is required for delete action",
                    )

                cmd: list[str] = ["git", "branch"]
                if params.force:
                    cmd.append("-D")
                else:
                    cmd.append("-d")
                cmd.append(params.branch_name)

                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to delete branch: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output=f"Branch '{params.branch_name}' deleted successfully",
                    metadata={"branch_name": params.branch_name},
                )

            elif action == "switch":
                if not params.branch_name:
                    return ToolResult.error_result(
                        "Branch name is required for switch action",
                    )

                cmd: list[str] = ["git", "checkout"]
                if params.force:
                    cmd.append("-f")
                cmd.append(params.branch_name)

                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to switch branch: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output=f"Switched to branch '{params.branch_name}'",
                    metadata={"branch_name": params.branch_name},
                )

            elif action == "show":
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to show current branch: {result.stderr}",
                        output=result.stdout,
                    )

                branch: str = result.stdout.strip()
                return ToolResult.success_result(
                    output=f"Current branch: {branch}",
                    metadata={"current_branch": branch},
                )

            else:
                return ToolResult.error_result(
                    f"Unknown action: {action}. "
                    "Valid actions: list, create, delete, switch, show",
                )

        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Git branch command timed out")
        except Exception as e:
            logger.exception(f"Failed to perform git branch operation: {e}")
            return ToolResult.error_result(
                f"Failed to perform git branch operation: {e}",
            )
