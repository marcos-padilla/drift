"""
Read file tool for reading text file contents.

This module provides a tool for reading text files with support for
line ranges, binary file detection, and output truncation.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.utils.paths import is_binary_file, resolve_path
from core.utils.text import Tokenizer

logger = logging.getLogger(__name__)


class ReadFileParams(BaseModel):
    """
    Parameters for the read_file tool.

    Parameters
    ----------
    path : str
        Path to the file to read (relative to working directory or absolute).
    offset : int, default=1
        Line number to start reading from (1-based).
    limit : int | None, optional
        Maximum number of lines to read. If not specified, reads entire file.

    Examples
    --------
    >>> params = ReadFileParams(path="test.py", offset=10, limit=20)
    """

    path: str = Field(
        ...,
        description="Path to the file to read (relative to working directory or absolute)",
    )
    offset: int = Field(
        1,
        ge=1,
        description="Line number to start reading from (1-based). Defaults to 1",
    )
    limit: int | None = Field(
        None,
        ge=1,
        description="Maximum number of lines to read. If not specified, reads entire file.",
    )


class ReadFileTool(Tool):
    """
    Tool for reading text file contents.

    This tool reads text files with support for line ranges, binary
    file detection, and automatic output truncation to stay within
    token limits.

    Attributes
    ----------
    name : str
        Tool name: "read_file"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[ReadFileParams]
        Parameter schema
    MAX_FILE_SIZE : int
        Maximum file size in bytes (10MB)
    MAX_OUTPUT_TOKENS : int
        Maximum output tokens (25000)
    """

    name: str = "read_file"
    description: str = (
        "Read the contents of a text file. Returns the file content with line numbers. "
        "For large files, use offset and limit to read specific portions. "
        "Cannot read binary files (images, executables, etc.)."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[ReadFileParams] = ReadFileParams

    MAX_FILE_SIZE: int = 1024 * 1024 * 10  # 10MB
    MAX_OUTPUT_TOKENS: int = 25000

    def __init__(self, config) -> None:
        super().__init__(config)
        self._tokenizer: Tokenizer = Tokenizer(model=self.config.model_name)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the read_file tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing file contents or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = ReadFileParams(**invocation.params)
        path: Path = resolve_path(invocation.cwd, params.path)

        if not path.exists():
            return ToolResult.error_result(f"File not found: {path}")

        if not path.is_file():
            return ToolResult.error_result(f"Path is not a file: {path}")

        file_size: int = path.stat().st_size

        if file_size > self.MAX_FILE_SIZE:
            return ToolResult.error_result(
                f"File too large ({file_size / (1024*1024):.1f}MB). "
                f"Maximum is {self.MAX_FILE_SIZE / (1024*1024):.0f}MB.",
            )

        if is_binary_file(path):
            file_size_mb: float = file_size / (1024 * 1024)
            size_str: str = (
                f"{file_size_mb:.2f}MB" if file_size_mb >= 1 else f"{file_size} bytes"
            )
            return ToolResult.error_result(
                f"Cannot read binary file: {path.name} ({size_str}) "
                f"This tool only reads text files.",
            )

        try:
            try:
                content: str = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")

            lines: list[str] = content.splitlines()
            total_lines: int = len(lines)

            if total_lines == 0:
                return ToolResult.success_result(
                    "File is empty.",
                    metadata={
                        "lines": 0,
                    },
                )

            start_idx: int = max(0, params.offset - 1)

            if params.limit is not None:
                end_idx: int = min(start_idx + params.limit, total_lines)
            else:
                end_idx: int = total_lines

            selected_lines: list[str] = lines[start_idx:end_idx]
            formatted_lines: list[str] = []

            for i, line in enumerate(selected_lines, start=start_idx + 1):
                formatted_lines.append(f"{i:6}|{line}")

            output: str = "\n".join(formatted_lines)
            token_count: int = self._tokenizer.count_tokens(output)

            truncated: bool = False
            if token_count > self.MAX_OUTPUT_TOKENS:
                output = self._tokenizer.truncate(
                    output,
                    self.MAX_OUTPUT_TOKENS,
                    suffix=f"\n... [truncated {total_lines} total lines]",
                )
                truncated = True

            metadata_lines: list[str] = []
            if start_idx > 0 or end_idx < total_lines:
                metadata_lines.append(
                    f"Showing lines {start_idx+1}-{end_idx} of {total_lines}",
                )

            if metadata_lines:
                header: str = " | ".join(metadata_lines) + "\n\n"
                output = header + output

            return ToolResult.success_result(
                output=output,
                truncated=truncated,
                metadata={
                    "path": str(path),
                    "total_lines": total_lines,
                    "shown_start": start_idx + 1,
                    "shown_end": end_idx,
                },
            )
        except Exception as e:
            logger.exception(f"Failed to read file {path}: {e}")
            return ToolResult.error_result(f"Failed to read file: {e}")
