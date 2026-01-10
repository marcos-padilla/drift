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
from core.tools.builtin.git_status import GitStatusTool
from core.tools.builtin.git_diff import GitDiffTool
from core.tools.builtin.git_log import GitLogTool
from core.tools.builtin.git_commit import GitCommitTool
from core.tools.builtin.git_branch import GitBranchTool
from core.tools.builtin.git_stash import GitStashTool
from core.tools.builtin.code_analysis import (
    FindImportsTool,
    FindDefinitionsTool,
    FindUsagesTool,
    CodeMetricsTool,
)
from core.tools.builtin.file_ops import (
    CopyFileTool,
    MoveFileTool,
    DeleteFileTool,
    CreateDirectoryTool,
)
from core.tools.builtin.code_quality import (
    FormatCodeTool,
    LintCodeTool,
    TypeCheckTool,
)
from core.tools.builtin.test_runner import RunTestsTool
from core.tools.builtin.dependencies import (
    ListDependenciesTool,
    CheckUpdatesTool,
)

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
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "GitCommitTool",
    "GitBranchTool",
    "GitStashTool",
    "FindImportsTool",
    "FindDefinitionsTool",
    "FindUsagesTool",
    "CodeMetricsTool",
    "CopyFileTool",
    "MoveFileTool",
    "DeleteFileTool",
    "CreateDirectoryTool",
    "FormatCodeTool",
    "LintCodeTool",
    "TypeCheckTool",
    "RunTestsTool",
    "ListDependenciesTool",
    "CheckUpdatesTool",
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
        GitStatusTool,
        GitDiffTool,
        GitLogTool,
        GitCommitTool,
        GitBranchTool,
        GitStashTool,
        FindImportsTool,
        FindDefinitionsTool,
        FindUsagesTool,
        CodeMetricsTool,
        CopyFileTool,
        MoveFileTool,
        DeleteFileTool,
        CreateDirectoryTool,
        FormatCodeTool,
        LintCodeTool,
        TypeCheckTool,
        RunTestsTool,
        ListDependenciesTool,
        CheckUpdatesTool,
    ]
