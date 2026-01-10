"""
Git commit tool for creating commits.

This module provides a tool for staging and committing changes with
safety checks for dangerous commits.
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

# Dangerous commit message patterns
DANGEROUS_PATTERNS: list[str] = [
    "force",
    "reset",
    "delete",
    "remove all",
    "wipe",
    "destroy",
    "drop database",
    "rm -rf",
]


class GitCommitParams(BaseModel):
    """
    Parameters for the git_commit tool.

    Parameters
    ----------
    path : str | None, optional
        Path to git repository (defaults to current directory).
    message : str
        Commit message.
    files : list[str] | None, optional
        Specific files to stage and commit. If not provided, stages all changes.
    allow_empty : bool, default=False
        Allow creating an empty commit.
    amend : bool, default=False
        Amend the previous commit instead of creating a new one.

    Examples
    --------
    >>> params = GitCommitParams(
    ...     path=".",
    ...     message="Fix bug in main.py",
    ...     files=["main.py"]
    ... )
    """

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current directory)",
    )
    message: str = Field(
        ...,
        description="Commit message",
    )
    files: list[str] | None = Field(
        None,
        description="Specific files to stage and commit (defaults to all changes)",
    )
    allow_empty: bool = Field(
        False,
        description="Allow creating an empty commit",
    )
    amend: bool = Field(
        False,
        description="Amend the previous commit instead of creating a new one",
    )


class GitCommitTool(Tool):
    """
    Tool for creating git commits.

    This tool stages and commits changes with safety checks for
    dangerous commit messages and operations.

    Attributes
    ----------
    name : str
        Tool name: "git_commit"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[GitCommitParams]
        Parameter schema
    """

    name: str = "git_commit"
    description: str = (
        "Stage and commit changes to git repository. Can commit specific "
        "files or all changes. Includes safety checks for dangerous operations."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[GitCommitParams] = GitCommitParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """
        Check if this operation modifies git history.

        Parameters
        ----------
        params : dict[str, Any]
            Tool parameters.

        Returns
        -------
        bool
            True (always mutating for commits).
        """
        return True

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for commit operations.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request if operation needs approval.
        """
        params = GitCommitParams(**invocation.params)
        repo_path: Path = (
            resolve_path(invocation.cwd, params.path)
            if params.path
            else invocation.cwd
        )

        # Check for dangerous patterns in commit message
        message_lower: str = params.message.lower()
        is_dangerous: bool = any(
            pattern in message_lower for pattern in DANGEROUS_PATTERNS
        )

        # Get list of files to be committed
        affected_paths: list[Path] = []
        if params.files:
            for file in params.files:
                file_path = resolve_path(repo_path, file)
                if file_path.exists():
                    affected_paths.append(file_path)
        else:
            # Check what files would be staged
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if line.strip():
                            file_status = line[3:].strip()
                            file_path = repo_path / file_status
                            if file_path.exists():
                                affected_paths.append(file_path)
            except Exception:
                pass

        description: str = f"Commit changes with message: {params.message}"
        if params.amend:
            description += " (amending previous commit)"
        if params.files:
            description += f"\nFiles: {', '.join(params.files)}"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=description,
            affected_paths=affected_paths,
            is_dangerous=is_dangerous,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the git_commit tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing commit output or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = GitCommitParams(**invocation.params)
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
            # Stage files
            if params.files:
                for file in params.files:
                    file_path = resolve_path(repo_path, file)
                    if not file_path.exists():
                        return ToolResult.error_result(f"File not found: {file}")

                    add_result = subprocess.run(
                        ["git", "add", str(file_path.relative_to(repo_path))],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if add_result.returncode != 0:
                        return ToolResult.error_result(
                            f"Failed to stage file {file}: {add_result.stderr}",
                        )
            else:
                # Stage all changes
                add_result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if add_result.returncode != 0:
                    return ToolResult.error_result(
                        f"Failed to stage changes: {add_result.stderr}",
                    )

            # Check if there are staged changes
            status_result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=repo_path,
                timeout=10,
            )
            if status_result.returncode == 0 and not params.allow_empty:
                return ToolResult.error_result(
                    "No changes staged for commit. Use allow_empty=true to create an empty commit.",
                )

            # Create commit
            cmd: list[str] = ["git", "commit", "-m", params.message]
            if params.amend:
                cmd.append("--amend")
            if params.allow_empty:
                cmd.append("--allow-empty")

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return ToolResult.error_result(
                    f"Git commit failed: {result.stderr}",
                    output=result.stdout,
                )

            # Get commit hash
            commit_hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            commit_hash: str = (
                commit_hash_result.stdout.strip()
                if commit_hash_result.returncode == 0
                else "unknown"
            )

            output: str = result.stdout
            if not output:
                output = f"Commit created successfully: {commit_hash[:8]}"

            return ToolResult.success_result(
                output=output,
                metadata={
                    "path": str(repo_path),
                    "commit_hash": commit_hash,
                    "message": params.message,
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Git commit command timed out")
        except Exception as e:
            logger.exception(f"Failed to create git commit: {e}")
            return ToolResult.error_result(f"Failed to create git commit: {e}")
