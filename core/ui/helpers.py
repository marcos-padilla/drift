"""
Helper functions for UI formatting and display.

This module provides utility functions for path display, code extraction,
language detection, and argument ordering used throughout the UI.
"""

import re
from pathlib import Path
from typing import Any

from core.utils.paths import display_path_relative_to_cwd


def display_path_rel_to_cwd(
    path: str | Path,
    cwd: Path | None,
) -> str:
    """
    Display a path relative to the current working directory.

    Parameters
    ----------
    path : str | Path
        Path to display.
    cwd : Path | None
        Current working directory. If None, uses absolute path.

    Returns
    -------
    str
        Relative path string if within CWD, otherwise absolute path.

    Examples
    --------
    >>> display_path_rel_to_cwd("/home/user/project/src/main.py", Path("/home/user/project"))
    'src/main.py'
    """
    if cwd is None:
        return str(path)
    return display_path_relative_to_cwd(path, cwd)


def extract_code_from_read_file_output(text: str) -> tuple[int, str] | None:
    """
    Extract code lines and starting line number from read_file output.

    Parameters
    ----------
    text : str
        Output text from read_file tool.

    Returns
    -------
    tuple[int, str] | None
        Tuple of (start_line, code) if code found, None otherwise.

    Examples
    --------
    >>> result = extract_code_from_read_file_output("1|def main():\\n2|    pass")
    >>> if result:
    ...     start_line, code = result
    ...     print(f"Starting at line {start_line}")
    """
    body: str = text
    # Handle "Showing lines X-Y of Z" header
    header_match = re.match(r"^Showing lines (\d+)-(\d+) of (\d+)\n\n", text)
    if header_match:
        body = text[header_match.end() :]

    code_lines: list[str] = []
    start_line: int | None = None

    for line in body.splitlines():
        # Match pattern: "  123|code content"
        match = re.match(r"^\s*(\d+)\|(.*)$", line)
        if not match:
            return None
        line_no: int = int(match.group(1))
        if start_line is None:
            start_line = line_no
        code_lines.append(match.group(2))

    if start_line is None:
        return None

    return start_line, "\n".join(code_lines)


def guess_language_from_path(path: str | Path | None) -> str:
    """
    Guess programming language from file path extension.

    Parameters
    ----------
    path : str | Path | None
        File path to analyze.

    Returns
    -------
    str
        Language name for syntax highlighting, or "text" if unknown.

    Examples
    --------
    >>> guess_language_from_path("main.py")
    'python'
    >>> guess_language_from_path("script.js")
    'javascript'
    """
    if not path:
        return "text"

    suffix: str = Path(path).suffix.lower()
    language_map: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".json": "json",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".kt": "kotlin",
        ".swift": "swift",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".css": "css",
        ".html": "html",
        ".xml": "xml",
        ".sql": "sql",
    }

    return language_map.get(suffix, "text")


def order_tool_arguments(
    tool_name: str,
    args: dict[str, Any],
) -> list[tuple[str, Any]]:
    """
    Order tool arguments in preferred display order.

    Parameters
    ----------
    tool_name : str
        Name of the tool.
    args : dict[str, Any]
        Tool arguments.

    Returns
    -------
    list[tuple[str, Any]]
        Ordered list of (key, value) tuples.

    Examples
    --------
    >>> args = {"content": "test", "path": "file.py", "create_directories": True}
    >>> ordered = order_tool_arguments("write_file", args)
    >>> # Returns: [("path", "file.py"), ("create_directories", True), ("content", "test")]
    """
    preferred_order: dict[str, list[str]] = {
        "read_file": ["path", "offset", "limit"],
        "write_file": ["path", "create_directories", "content"],
        "edit": ["path", "replace_all", "old_string", "new_string"],
        "shell": ["command", "timeout", "cwd"],
        "list_dir": ["path", "include_hidden"],
        "grep": ["path", "case_insensitive", "pattern"],
        "glob": ["path", "pattern"],
        "todos": ["id", "action", "content"],
        "memory": ["action", "key", "value"],
    }

    preferred: list[str] = preferred_order.get(tool_name, [])
    ordered: list[tuple[str, Any]] = []
    seen: set[str] = set()

    # Add preferred keys first
    for key in preferred:
        if key in args:
            ordered.append((key, args[key]))
            seen.add(key)

    # Add remaining keys
    remaining_keys: set[str] = set(args.keys()) - seen
    ordered.extend((key, args[key]) for key in remaining_keys)

    return ordered
