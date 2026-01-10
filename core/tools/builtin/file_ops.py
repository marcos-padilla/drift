"""
File operations tools for copying, moving, deleting, and creating directories.

This module provides tools for common file system operations with safety
checks and proper error handling.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from core.tools.registration.decorator import register_tool
from core.utils.paths import resolve_path, validate_path_within_base

logger = logging.getLogger(__name__)


class CopyFileParams(BaseModel):
    """
    Parameters for the copy_file tool.

    Parameters
    ----------
    source : str
        Source file or directory path.
    destination : str
        Destination path.
    preserve_metadata : bool, default=True
        Preserve file metadata (timestamps, permissions).

    Examples
    --------
    >>> params = CopyFileParams(source="file.txt", destination="backup/file.txt")
    """

    source: str = Field(..., description="Source file or directory path")
    destination: str = Field(..., description="Destination path")
    preserve_metadata: bool = Field(
        True,
        description="Preserve file metadata (timestamps, permissions)",
    )


class MoveFileParams(BaseModel):
    """
    Parameters for the move_file tool.

    Parameters
    ----------
    source : str
        Source file or directory path.
    destination : str
        Destination path.

    Examples
    --------
    >>> params = MoveFileParams(source="old_name.txt", destination="new_name.txt")
    """

    source: str = Field(..., description="Source file or directory path")
    destination: str = Field(..., description="Destination path")


class DeleteFileParams(BaseModel):
    """
    Parameters for the delete_file tool.

    Parameters
    ----------
    path : str
        File or directory path to delete.
    recursive : bool, default=False
        Delete directories recursively.

    Examples
    --------
    >>> params = DeleteFileParams(path="temp/", recursive=True)
    """

    path: str = Field(..., description="File or directory path to delete")
    recursive: bool = Field(
        False,
        description="Delete directories recursively",
    )


class CreateDirectoryParams(BaseModel):
    """
    Parameters for the create_directory tool.

    Parameters
    ----------
    path : str
        Directory path to create.
    parents : bool, default=True
        Create parent directories if they don't exist.

    Examples
    --------
    >>> params = CreateDirectoryParams(path="new/directory/", parents=True)
    """

    path: str = Field(..., description="Directory path to create")
    parents: bool = Field(
        True,
        description="Create parent directories if they don't exist",
    )


@register_tool(name="copy_file", description="Copy files or directories")
class CopyFileTool(Tool):
    """
    Tool for copying files and directories.

    This tool copies files or directories with optional metadata preservation
    and safety checks.

    Attributes
    ----------
    name : str
        Tool name: "copy_file"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[CopyFileParams]
        Parameter schema
    """

    name: str = "copy_file"
    description: str = (
        "Copy a file or directory to a new location. Supports preserving "
        "file metadata and recursive directory copying."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[CopyFileParams] = CopyFileParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if this operation modifies the file system."""
        return True

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """Get confirmation request for copy operations."""
        params = CopyFileParams(**invocation.params)
        source_path: Path = resolve_path(invocation.cwd, params.source)
        dest_path: Path = resolve_path(invocation.cwd, params.destination)

        # Check if destination exists
        is_dangerous: bool = dest_path.exists()

        description: str = f"Copy {params.source} to {params.destination}"
        if is_dangerous:
            description += "\n⚠️  Destination already exists and will be overwritten"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=description,
            affected_paths=[dest_path],
            is_dangerous=is_dangerous,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the copy_file tool."""
        params = CopyFileParams(**invocation.params)
        source_path: Path = resolve_path(invocation.cwd, params.source)
        dest_path: Path = resolve_path(invocation.cwd, params.destination)

        # Validate paths are within workspace
        try:
            source_path = validate_path_within_base(source_path, invocation.cwd)
            dest_path = validate_path_within_base(dest_path, invocation.cwd)
        except Exception as e:
            return ToolResult.error_result(str(e))

        if not source_path.exists():
            return ToolResult.error_result(f"Source does not exist: {params.source}")

        try:
            if source_path.is_file():
                shutil.copy2(source_path, dest_path)
                if not params.preserve_metadata:
                    # Reset metadata if not preserving
                    dest_path.touch()
            elif source_path.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(
                    source_path,
                    dest_path,
                    dirs_exist_ok=True,
                )
            else:
                return ToolResult.error_result(
                    f"Source is not a file or directory: {params.source}",
                )

            return ToolResult.success_result(
                output=f"Copied {params.source} to {params.destination}",
                metadata={
                    "source": str(source_path),
                    "destination": str(dest_path),
                },
            )
        except Exception as e:
            logger.exception(f"Failed to copy file: {e}")
            return ToolResult.error_result(f"Failed to copy: {e}")


@register_tool(name="move_file", description="Move or rename files/directories")
class MoveFileTool(Tool):
    """
    Tool for moving and renaming files and directories.

    This tool moves or renames files/directories with atomic operations
    where possible.

    Attributes
    ----------
    name : str
        Tool name: "move_file"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[MoveFileParams]
        Parameter schema
    """

    name: str = "move_file"
    description: str = (
        "Move or rename a file or directory. This is an atomic operation "
        "when possible."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[MoveFileParams] = MoveFileParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if this operation modifies the file system."""
        return True

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """Get confirmation request for move operations."""
        params = MoveFileParams(**invocation.params)
        source_path: Path = resolve_path(invocation.cwd, params.source)
        dest_path: Path = resolve_path(invocation.cwd, params.destination)

        # Check if destination exists
        is_dangerous: bool = dest_path.exists()

        description: str = f"Move {params.source} to {params.destination}"
        if is_dangerous:
            description += "\n⚠️  Destination already exists and will be overwritten"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=description,
            affected_paths=[source_path, dest_path],
            is_dangerous=is_dangerous,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the move_file tool."""
        params = MoveFileParams(**invocation.params)
        source_path: Path = resolve_path(invocation.cwd, params.source)
        dest_path: Path = resolve_path(invocation.cwd, params.destination)

        # Validate paths are within workspace
        try:
            source_path = validate_path_within_base(source_path, invocation.cwd)
            dest_path = validate_path_within_base(dest_path, invocation.cwd)
        except Exception as e:
            return ToolResult.error_result(str(e))

        if not source_path.exists():
            return ToolResult.error_result(f"Source does not exist: {params.source}")

        try:
            # Ensure destination parent exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(source_path), str(dest_path))

            return ToolResult.success_result(
                output=f"Moved {params.source} to {params.destination}",
                metadata={
                    "source": str(source_path),
                    "destination": str(dest_path),
                },
            )
        except Exception as e:
            logger.exception(f"Failed to move file: {e}")
            return ToolResult.error_result(f"Failed to move: {e}")


@register_tool(name="delete_file", description="Delete files or directories")
class DeleteFileTool(Tool):
    """
    Tool for deleting files and directories.

    This tool deletes files or directories with safety checks and
    recursive deletion support.

    Attributes
    ----------
    name : str
        Tool name: "delete_file"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[DeleteFileParams]
        Parameter schema
    """

    name: str = "delete_file"
    description: str = (
        "Delete a file or directory. Supports recursive deletion for "
        "directories. Includes safety checks."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[DeleteFileParams] = DeleteFileParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if this operation modifies the file system."""
        return True

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """Get confirmation request for delete operations."""
        params = DeleteFileParams(**invocation.params)
        target_path: Path = resolve_path(invocation.cwd, params.path)

        is_dangerous: bool = True  # Deletion is always dangerous
        description: str = f"Delete {params.path}"

        if target_path.is_dir():
            if params.recursive:
                description += " (recursive - will delete all contents)"
            else:
                description += "\n⚠️  Directory is not empty, use recursive=true to delete"

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=description,
            affected_paths=[target_path],
            is_dangerous=is_dangerous,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the delete_file tool."""
        params = DeleteFileParams(**invocation.params)
        target_path: Path = resolve_path(invocation.cwd, params.path)

        # Validate path is within workspace
        try:
            target_path = validate_path_within_base(target_path, invocation.cwd)
        except Exception as e:
            return ToolResult.error_result(str(e))

        if not target_path.exists():
            return ToolResult.error_result(f"Path does not exist: {params.path}")

        try:
            if target_path.is_file():
                target_path.unlink()
            elif target_path.is_dir():
                if params.recursive:
                    shutil.rmtree(target_path)
                else:
                    # Check if directory is empty
                    if any(target_path.iterdir()):
                        return ToolResult.error_result(
                            f"Directory is not empty: {params.path}. "
                            "Use recursive=true to delete non-empty directories.",
                        )
                    target_path.rmdir()
            else:
                return ToolResult.error_result(
                    f"Path is not a file or directory: {params.path}",
                )

            return ToolResult.success_result(
                output=f"Deleted {params.path}",
                metadata={"path": str(target_path)},
            )
        except Exception as e:
            logger.exception(f"Failed to delete: {e}")
            return ToolResult.error_result(f"Failed to delete: {e}")


@register_tool(name="create_directory", description="Create directories")
class CreateDirectoryTool(Tool):
    """
    Tool for creating directories.

    This tool creates directories with optional parent directory creation.

    Attributes
    ----------
    name : str
        Tool name: "create_directory"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[CreateDirectoryParams]
        Parameter schema
    """

    name: str = "create_directory"
    description: str = (
        "Create a directory. Can create parent directories if they don't exist."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[CreateDirectoryParams] = CreateDirectoryParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if this operation modifies the file system."""
        return True

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the create_directory tool."""
        params = CreateDirectoryParams(**invocation.params)
        dir_path: Path = resolve_path(invocation.cwd, params.path)

        # Validate path is within workspace
        try:
            dir_path = validate_path_within_base(dir_path, invocation.cwd)
        except Exception as e:
            return ToolResult.error_result(str(e))

        if dir_path.exists():
            if dir_path.is_dir():
                return ToolResult.success_result(
                    output=f"Directory already exists: {params.path}",
                )
            else:
                return ToolResult.error_result(
                    f"Path exists but is not a directory: {params.path}",
                )

        try:
            dir_path.mkdir(parents=params.parents, exist_ok=True)

            return ToolResult.success_result(
                output=f"Created directory: {params.path}",
                metadata={"path": str(dir_path)},
            )
        except Exception as e:
            logger.exception(f"Failed to create directory: {e}")
            return ToolResult.error_result(f"Failed to create directory: {e}")
