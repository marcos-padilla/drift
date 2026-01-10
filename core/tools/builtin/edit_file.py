"""
Edit file tool for making precise text replacements.

This module provides a tool for editing files by replacing specific
text patterns with support for single or multiple replacements.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import FileDiff, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from core.utils.paths import ensure_parent_directory, resolve_path

logger = logging.getLogger(__name__)


class EditParams(BaseModel):
    """
    Parameters for the edit tool.

    Parameters
    ----------
    path : str
        Path to the file to edit (relative to working directory or absolute path).
    old_string : str, default=""
        The exact text to find and replace. Must match exactly including all whitespace.
        For new files, leave this empty.
    new_string : str
        The text to replace old_string with. Can be empty to delete text.
    replace_all : bool, default=False
        Replace all occurrences of old_string (default: false).

    Examples
    --------
    >>> params = EditParams(
    ...     path="test.py",
    ...     old_string="print('old')",
    ...     new_string="print('new')"
    ... )
    """

    path: str = Field(
        ...,
        description="Path to the file to edit (relative to working directory or absolute path)",
    )
    old_string: str = Field(
        "",
        description="The exact text to find and replace. Must match exactly including all whitespace and indentation. For new files, leave this empty.",
    )
    new_string: str = Field(
        ...,
        description="The text to replace old_string with. Can be empty to delete text",
    )
    replace_all: bool = Field(
        False,
        description="Replace all occurrences of old_string (default: false)",
    )


class EditTool(Tool):
    """
    Tool for editing files by replacing text.

    This tool performs precise text replacements in files, with support
    for creating new files and replacing single or multiple occurrences.

    Attributes
    ----------
    name : str
        Tool name: "edit"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[EditParams]
        Parameter schema
    """

    name: str = "edit"
    description: str = (
        "Edit a file by replacing text. The old_string must match exactly "
        "(including whitespace and indentation) and must be unique in the file "
        "unless replace_all is true. Use this for precise, surgical edits. "
        "For creating new files or complete rewrites, use write_file instead."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[EditParams] = EditParams

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for file edit operation.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request with file diff.
        """
        params = EditParams(**invocation.params)
        path: Path = resolve_path(invocation.cwd, params.path)

        is_new_file: bool = not path.exists()

        if is_new_file:
            diff = FileDiff(
                path=path,
                old_content="",
                new_content=params.new_string,
                is_new_file=True,
            )

            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"Create new file: {path}",
                diff=diff,
                affected_paths=[path],
            )

        old_content: str = path.read_text(encoding="utf-8")

        if params.replace_all:
            new_content: str = old_content.replace(params.old_string, params.new_string)
        else:
            new_content = old_content.replace(params.old_string, params.new_string, 1)

        diff = FileDiff(
            path=path,
            old_content=old_content,
            new_content=new_content,
        )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Edit file: {path}",
            diff=diff,
            affected_paths=[path],
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the edit tool.

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
        params = EditParams(**invocation.params)
        path: Path = resolve_path(invocation.cwd, params.path)

        if not path.exists():
            if params.old_string:
                return ToolResult.error_result(
                    f"File does not exist: {path}. "
                    f"To create a new file, use an empty old_string.",
                )

            ensure_parent_directory(path)
            path.write_text(params.new_string, encoding="utf-8")

            line_count: int = len(params.new_string.splitlines())

            return ToolResult.success_result(
                f"Created {path} {line_count} lines",
                diff=FileDiff(
                    path=path,
                    old_content="",
                    new_content=params.new_string,
                    is_new_file=True,
                ),
                metadata={
                    "path": str(path),
                    "is_new_file": True,
                    "lines": line_count,
                },
            )

        old_content: str = path.read_text(encoding="utf-8")

        if not params.old_string:
            return ToolResult.error_result(
                "old_string is empty but file exists. "
                "Provide old_string to edit, or use write_file to overwrite.",
            )

        occurrence_count: int = old_content.count(params.old_string)

        if occurrence_count == 0:
            return self._no_match_error(params.old_string, old_content, path)

        if occurrence_count > 1 and not params.replace_all:
            return ToolResult.error_result(
                f"old_string found {occurrence_count} times in {path}. "
                f"Either: \n"
                f"1. Provide more context to make the match unique or\n"
                f"2. Set replace_all=true to replace all occurrences",
                metadata={
                    "occurrence_count": occurrence_count,
                },
            )

        if params.replace_all:
            new_content = old_content.replace(params.old_string, params.new_string)
            replace_count: int = occurrence_count
        else:
            new_content = old_content.replace(params.old_string, params.new_string, 1)
            replace_count = 1

        if new_content == old_content:
            return ToolResult.error_result(
                "No change made - old_string equals new_string",
            )

        try:
            path.write_text(new_content, encoding="utf-8")
        except OSError as e:
            logger.exception(f"Failed to write file {path}: {e}")
            return ToolResult.error_result(f"Failed to write file: {e}")

        old_lines: int = len(old_content.splitlines())
        new_lines: int = len(new_content.splitlines())
        line_diff: int = new_lines - old_lines

        diff_msg: str = ""
        if line_diff > 0:
            diff_msg = f" (+{line_diff} lines)"
        elif line_diff < 0:
            diff_msg = f" ({line_diff} lines)"

        return ToolResult.success_result(
            f"Edited {path}: replaced {replace_count} occurrence(s){diff_msg}",
            diff=FileDiff(
                path=path,
                old_content=old_content,
                new_content=new_content,
            ),
            metadata={
                "path": str(path),
                "replaced_count": replace_count,
                "line_diff": line_diff,
            },
        )

    def _no_match_error(
        self,
        old_string: str,
        content: str,
        path: Path,
    ) -> ToolResult:
        """
        Generate error message when old_string is not found.

        Parameters
        ----------
        old_string : str
            The string that was not found.
        content : str
            File content.
        path : Path
            File path.

        Returns
        -------
        ToolResult
            Error result with helpful suggestions.
        """
        lines: list[str] = content.splitlines()

        partial_matches: list[tuple[int, str]] = []
        search_terms: list[str] = old_string.split()[:5]

        if search_terms:
            first_term: str = search_terms[0]
            for i, line in enumerate(lines, 1):
                if first_term in line:
                    partial_matches.append((i, line.strip()[:80]))
                    if len(partial_matches) >= 3:
                        break

        error_msg: str = f"old_string not found in {path}."

        if partial_matches:
            error_msg += "\n\nPossible similar lines:"
            for line_num, line_preview in partial_matches:
                error_msg += f"\n  Line {line_num}: {line_preview}"
            error_msg += (
                "\n\nMake sure old_string matches exactly "
                "(including whitespace and indentation)."
            )
        else:
            error_msg += (
                " Make sure the text matches exactly, including:\n"
                "- All whitespace and indentation\n"
                "- Line breaks\n"
                "- Any invisible characters\n"
                "Try re-reading the file using read_file tool and then editing."
            )

        return ToolResult.error_result(error_msg)
