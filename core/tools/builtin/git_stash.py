"""
Git stash tool for stash operations.

This module provides a tool for saving, applying, deleting, and listing
git stashes.
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


class GitStashParams(BaseModel):
    """
    Parameters for the git_stash tool.

    Parameters
    ----------
    path : str | None, optional
        Path to git repository (defaults to current directory).
    action : str
        Action to perform: "list", "save", "apply", "pop", or "drop".
    message : str | None, optional
        Stash message (for save action).
    stash_index : int | None, optional
        Stash index (for apply, pop, drop actions, default: 0 for most recent).

    Examples
    --------
    >>> params = GitStashParams(path=".", action="list")
    >>> params = GitStashParams(path=".", action="save", message="WIP: feature")
    """

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current directory)",
    )
    action: str = Field(
        ...,
        description="Action: 'list', 'save', 'apply', 'pop', or 'drop'",
    )
    message: str | None = Field(
        None,
        description="Stash message (for save action)",
    )
    stash_index: int | None = Field(
        None,
        description="Stash index (for apply, pop, drop, default: 0 for most recent)",
    )


class GitStashTool(Tool):
    """
    Tool for git stash operations.

    This tool can list, save, apply, pop, and drop stashes with
    appropriate safety checks.

    Attributes
    ----------
    name : str
        Tool name: "git_stash"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE (for mutating operations)
    schema : type[GitStashParams]
        Parameter schema
    """

    name: str = "git_stash"
    description: str = (
        "Perform git stash operations: list stashes, save changes to stash, "
        "apply or pop stashes, and delete stashes."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[GitStashParams] = GitStashParams

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
            True for save, apply, pop, drop; False for list.
        """
        action: str = params.get("action", "")
        return action != "list"

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for stash operations.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request if operation needs approval.
        """
        params = GitStashParams(**invocation.params)
        action: str = params.action

        if action == "list":
            return None

        is_dangerous: bool = action == "drop"
        description: str = f"{action.capitalize()} stash"

        if action == "drop":
            stash_idx: str = str(params.stash_index) if params.stash_index is not None else "0"
            description += f" (index: {stash_idx})\n⚠️  This will permanently delete the stash"
        elif action == "pop":
            description += "\n⚠️  This will apply and delete the stash"
        elif action == "apply":
            description += "\n⚠️  This will apply stash changes (may cause conflicts)"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=description,
            is_dangerous=is_dangerous,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the git_stash tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing stash operation output or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GitStashParams(**invocation.params)
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
                    ["git", "stash", "list"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Git stash list failed: {result.stderr}",
                        output=result.stdout,
                    )

                output: str = result.stdout
                if not output:
                    output = "No stashes found."

                return ToolResult.success_result(
                    output=output,
                    metadata={"count": len(output.splitlines())},
                )

            elif action == "save":
                cmd: list[str] = ["git", "stash", "push"]
                if params.message:
                    cmd.extend(["-m", params.message])

                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to save stash: {result.stderr}",
                        output=result.stdout,
                    )

                output: str = result.stdout
                if not output:
                    output = "Changes stashed successfully"
                if params.message:
                    output += f"\nMessage: {params.message}"

                return ToolResult.success_result(
                    output=output,
                    metadata={"message": params.message},
                )

            elif action == "apply":
                stash_ref: str = (
                    f"stash@{{{params.stash_index}}}"
                    if params.stash_index is not None
                    else "stash@{0}"
                )

                result = subprocess.run(
                    ["git", "stash", "apply", stash_ref],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to apply stash: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output="Stash applied successfully",
                    metadata={"stash_index": params.stash_index or 0},
                )

            elif action == "pop":
                stash_ref: str = (
                    f"stash@{{{params.stash_index}}}"
                    if params.stash_index is not None
                    else "stash@{0}"
                )

                result = subprocess.run(
                    ["git", "stash", "pop", stash_ref],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to pop stash: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output="Stash popped successfully (applied and removed)",
                    metadata={"stash_index": params.stash_index or 0},
                )

            elif action == "drop":
                stash_ref: str = (
                    f"stash@{{{params.stash_index}}}"
                    if params.stash_index is not None
                    else "stash@{0}"
                )

                result = subprocess.run(
                    ["git", "stash", "drop", stash_ref],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to drop stash: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output=f"Stash {stash_ref} dropped successfully",
                    metadata={"stash_index": params.stash_index or 0},
                )

            else:
                return ToolResult.error_result(
                    f"Unknown action: {action}. "
                    "Valid actions: list, save, apply, pop, drop",
                )

        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Git stash command timed out")
        except Exception as e:
            logger.exception(f"Failed to perform git stash operation: {e}")
            return ToolResult.error_result(
                f"Failed to perform git stash operation: {e}",
            )
