"""
Tool output formatters for rich display.

This module provides formatter functions for different tool types,
creating rich renderable objects with syntax highlighting and
appropriate formatting for each tool's output.
"""

from pathlib import Path
from typing import Any

from rich.console import Group
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from core.ui.helpers import (
    display_path_rel_to_cwd,
    extract_code_from_read_file_output,
    guess_language_from_path,
    order_tool_arguments,
)
from core.utils.text import truncate_text

# Maximum tokens for tool output blocks
MAX_BLOCK_TOKENS: int = 2500


def format_tool_arguments_table(
    tool_name: str,
    args: dict[str, Any],
    cwd: Path | None,
) -> Table:
    """
    Create a rich Table displaying tool arguments.

    Parameters
    ----------
    tool_name : str
        Name of the tool.
    args : dict[str, Any]
        Tool arguments.
    cwd : Path | None
        Current working directory for path display.

    Returns
    -------
    Table
        Rich table with formatted arguments.

    Examples
    --------
    >>> table = format_tool_arguments_table("read_file", {"path": "test.py"}, Path.cwd())
    """
    table = Table.grid(padding=(0, 1))
    table.add_column(style="muted", justify="right", no_wrap=True)
    table.add_column(style="code", overflow="fold")

    for key, value in order_tool_arguments(tool_name, args):
        # Format value for display
        display_value: Any = value

        if isinstance(value, str):
            # Special handling for large text fields
            if key in {"content", "old_string", "new_string"}:
                line_count: int = len(value.splitlines()) or 0
                byte_count: int = len(value.encode("utf-8", errors="replace"))
                display_value = f"<{line_count} lines • {byte_count} bytes>"
        elif isinstance(value, bool):
            display_value = str(value)
        elif isinstance(value, (list, dict)):
            display_value = str(value)

        # Display paths relative to CWD
        if key in {"path", "cwd"} and isinstance(value, str) and cwd:
            display_value = display_path_rel_to_cwd(value, cwd)

        table.add_row(key, str(display_value))

    return table


def format_read_file_output(
    name: str,
    output: str,
    metadata: dict[str, Any] | None,
    cwd: Path | None,
    model_name: str,
) -> Group:
    """
    Format read_file tool output with syntax highlighting.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    metadata : dict[str, Any] | None
        Tool metadata.
    cwd : Path | None
        Current working directory.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_read_file_output(
    ...     "read_file", "1|def main():\\n2|    pass",
    ...     {"path": "main.py"}, Path.cwd(), "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    primary_path: str | None = None
    if isinstance(metadata, dict) and isinstance(metadata.get("path"), str):
        primary_path = metadata.get("path")

    # Extract code from output
    code_result = extract_code_from_read_file_output(output)
    if code_result and primary_path:
        start_line: int
        code: str
        start_line, code = code_result

        shown_start: int | None = metadata.get("shown_start") if metadata else None
        shown_end: int | None = metadata.get("shown_end") if metadata else None
        total_lines: int | None = metadata.get("total_lines") if metadata else None

        language: str = guess_language_from_path(primary_path)

        # Create header
        header_parts: list[str] = [display_path_rel_to_cwd(primary_path, cwd)]
        if shown_start and shown_end and total_lines:
            header_parts.append(f" • lines {shown_start}-{shown_end} of {total_lines}")

        blocks.append(Text(" • ".join(header_parts), style="muted"))
        blocks.append(
            Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=True,
                start_line=start_line,
                word_wrap=False,
            ),
        )
    else:
        # Fallback: display as text
        output_display: str = truncate_text(
            output,
            model_name,
            MAX_BLOCK_TOKENS,
        )
        blocks.append(
            Syntax(
                output_display,
                "text",
                theme="monokai",
                word_wrap=False,
            ),
        )

    return Group(*blocks)


def format_write_file_output(
    name: str,
    output: str,
    diff: str | None,
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format write_file tool output with diff display.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    diff : str | None
        File diff if available.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_write_file_output(
    ...     "write_file", "Created file.py", "--- a/file.py\\n+++ b/file.py",
    ...     None, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    output_line: str = output.strip() if output.strip() else "Completed"
    blocks.append(Text(output_line, style="muted"))

    if diff:
        diff_display: str = truncate_text(
            diff,
            model_name,
            MAX_BLOCK_TOKENS,
        )
        blocks.append(
            Syntax(
                diff_display,
                "diff",
                theme="monokai",
                word_wrap=True,
            ),
        )

    return Group(*blocks)


def format_shell_output(
    name: str,
    output: str,
    args: dict[str, Any],
    exit_code: int | None,
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format shell command output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    args : dict[str, Any]
        Tool arguments.
    exit_code : int | None
        Exit code from command.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_shell_output(
    ...     "shell", "Hello world", {"command": "echo hello"}, 0, None, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    command: str | None = args.get("command")
    if isinstance(command, str) and command.strip():
        blocks.append(Text(f"$ {command.strip()}", style="muted"))

    if exit_code is not None:
        blocks.append(Text(f"exit_code={exit_code}", style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_list_dir_output(
    name: str,
    output: str,
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format list_dir tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_list_dir_output(
    ...     "list_dir", "file1.py\\nfile2.py", {"entries": 2}, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    entries: int | None = metadata.get("entries") if metadata else None
    path: str | None = metadata.get("path") if metadata else None

    summary: list[str] = []
    if isinstance(path, str):
        summary.append(path)
    if isinstance(entries, int):
        summary.append(f"{entries} entries")

    if summary:
        blocks.append(Text(" • ".join(summary), style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_grep_output(
    name: str,
    output: str,
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format grep tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_grep_output(
    ...     "grep", "file.py:10:pattern", {"matches": 1, "files_searched": 1}, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    matches: int | None = metadata.get("matches") if metadata else None
    files_searched: int | None = metadata.get("files_searched") if metadata else None

    summary: list[str] = []
    if isinstance(matches, int):
        summary.append(f"{matches} matches")
    if isinstance(files_searched, int):
        summary.append(f"searched {files_searched} files")

    if summary:
        blocks.append(Text(" • ".join(summary), style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_glob_output(
    name: str,
    output: str,
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format glob tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_glob_output(
    ...     "glob", "file1.py\\nfile2.py", {"matches": 2}, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    matches: int | None = metadata.get("matches") if metadata else None
    if isinstance(matches, int):
        blocks.append(Text(f"{matches} matches", style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_web_search_output(
    name: str,
    output: str,
    args: dict[str, Any],
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format web_search tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    args : dict[str, Any]
        Tool arguments.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_web_search_output(
    ...     "web_search", "Results...", {"query": "python"}, {"results": 10}, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    results: int | None = metadata.get("results") if metadata else None
    query: str | None = args.get("query") if args else None

    summary: list[str] = []
    if isinstance(query, str):
        summary.append(query)
    if isinstance(results, int):
        summary.append(f"{results} results")

    if summary:
        blocks.append(Text(" • ".join(summary), style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_web_fetch_output(
    name: str,
    output: str,
    args: dict[str, Any],
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format web_fetch tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    args : dict[str, Any]
        Tool arguments.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_web_fetch_output(
    ...     "web_fetch", "<html>...</html>", {"url": "https://example.com"},
    ...     {"status_code": 200}, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    status_code: int | None = metadata.get("status_code") if metadata else None
    content_length: int | None = metadata.get("content_length") if metadata else None
    url: str | None = args.get("url") if args else None

    summary: list[str] = []
    if isinstance(status_code, int):
        summary.append(str(status_code))
    if isinstance(content_length, int):
        summary.append(f"{content_length} bytes")
    if isinstance(url, str):
        summary.append(url)

    if summary:
        blocks.append(Text(" • ".join(summary), style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_todos_output(
    name: str,
    output: str,
    model_name: str,
) -> Group:
    """
    Format todos tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_todos_output("todos", "Todos:\\n  [123] Task", "gpt-4o")
    """
    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    return Group(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )


def format_memory_output(
    name: str,
    output: str,
    args: dict[str, Any],
    metadata: dict[str, Any] | None,
    model_name: str,
) -> Group:
    """
    Format memory tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    args : dict[str, Any]
        Tool arguments.
    metadata : dict[str, Any] | None
        Tool metadata.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_memory_output(
    ...     "memory", "Memory found: key: value", {"action": "get", "key": "key"},
    ...     {"found": True}, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    action: str | None = args.get("action") if args else None
    key: str | None = args.get("key") if args else None
    found: bool | None = metadata.get("found") if metadata else None

    summary: list[str] = []
    if isinstance(action, str) and action:
        summary.append(action)
    if isinstance(key, str) and key:
        summary.append(key)
    if isinstance(found, bool):
        summary.append("found" if found else "missing")

    if summary:
        blocks.append(Text(" • ".join(summary), style="muted"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    blocks.append(
        Syntax(
            output_display,
            "text",
            theme="monokai",
            word_wrap=True,
        ),
    )

    return Group(*blocks)


def format_generic_output(
    name: str,
    output: str,
    error: str | None,
    success: bool,
    model_name: str,
) -> Group:
    """
    Format generic tool output.

    Parameters
    ----------
    name : str
        Tool name.
    output : str
        Tool output text.
    error : str | None
        Error message if failed.
    success : bool
        Whether the tool succeeded.
    model_name : str
        Model name for tokenization.

    Returns
    -------
    Group
        Rich group with formatted output.

    Examples
    --------
    >>> group = format_generic_output(
    ...     "unknown_tool", "Some output", None, True, "gpt-4o"
    ... )
    """
    blocks: list[Any] = []

    if error and not success:
        blocks.append(Text(error, style="error"))

    output_display: str = truncate_text(
        output,
        model_name,
        MAX_BLOCK_TOKENS,
    )
    if output_display.strip():
        blocks.append(
            Syntax(
                output_display,
                "text",
                theme="monokai",
                word_wrap=True,
            ),
        )
    else:
        blocks.append(Text("(no output)", style="muted"))

    return Group(*blocks)
