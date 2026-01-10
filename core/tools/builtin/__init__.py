"""
Builtin tools for the Drift framework.

This package provides standard tools for file operations, shell commands,
web requests, and other common operations.
"""

from core.tools.builtin.edit_file import EditTool
from core.tools.builtin.glob import GlobTool
from core.tools.builtin.grep import GrepTool
from core.tools.builtin.list_dir import ListDirTool
from core.tools.builtin.memory import MemoryTool
from core.tools.builtin.read_file import ReadFileTool
from core.tools.builtin.shell import ShellTool
from core.tools.builtin.todo import TodosTool
from core.tools.builtin.web_fetch import WebFetchTool
from core.tools.builtin.web_search import WebSearchTool
from core.tools.builtin.write_file import WriteFileTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
    "GlobTool",
    "WebSearchTool",
    "WebFetchTool",
    "TodosTool",
    "MemoryTool",
]


def get_all_builtin_tools() -> list[type]:
    """
    Get all builtin tool classes.

    Returns
    -------
    list[type]
        List of tool classes.

    Examples
    --------
    >>> tools = get_all_builtin_tools()
    >>> for tool_class in tools:
    ...     print(tool_class.name)
    """
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool,
    ]
