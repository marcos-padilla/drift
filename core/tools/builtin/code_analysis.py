"""
Code analysis tools for finding imports, definitions, usages, and metrics.

This module provides tools for analyzing codebases including finding imports,
function/class definitions, symbol usages, and calculating code metrics.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.tools.registration.decorator import register_tool
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class FindImportsParams(BaseModel):
    """
    Parameters for the find_imports tool.

    Parameters
    ----------
    path : str
        File or directory to search in.
    module : str | None, optional
        Filter by specific module name.
    file_pattern : str | None, optional
        Filter files by pattern (e.g., "*.py").

    Examples
    --------
    >>> params = FindImportsParams(path="src/", module="os")
    """

    path: str = Field(..., description="File or directory to search in")
    module: str | None = Field(None, description="Filter by specific module name")
    file_pattern: str | None = Field(
        None,
        description="Filter files by pattern (e.g., '*.py')",
    )


class FindDefinitionsParams(BaseModel):
    """
    Parameters for the find_definitions tool.

    Parameters
    ----------
    path : str
        File or directory to search in.
    name_pattern : str
        Pattern to match function/class names (supports regex).
    kind : str | None, optional
        Filter by kind: "function", "class", or None for both.

    Examples
    --------
    >>> params = FindDefinitionsParams(path="src/", name_pattern="^get_.*")
    """

    path: str = Field(..., description="File or directory to search in")
    name_pattern: str = Field(
        ...,
        description="Pattern to match function/class names (supports regex)",
    )
    kind: str | None = Field(
        None,
        description="Filter by kind: 'function', 'class', or None for both",
    )


class FindUsagesParams(BaseModel):
    """
    Parameters for the find_usages tool.

    Parameters
    ----------
    path : str
        File or directory to search in.
    symbol : str
        Symbol name to find usages of.
    exact : bool, default=True
        Match exact symbol name only.

    Examples
    --------
    >>> params = FindUsagesParams(path="src/", symbol="get_user")
    """

    path: str = Field(..., description="File or directory to search in")
    symbol: str = Field(..., description="Symbol name to find usages of")
    exact: bool = Field(
        True,
        description="Match exact symbol name only (default: True)",
    )


class CodeMetricsParams(BaseModel):
    """
    Parameters for the code_metrics tool.

    Parameters
    ----------
    path : str
        File or directory to analyze.

    Examples
    --------
    >>> params = CodeMetricsParams(path="src/")
    """

    path: str = Field(..., description="File or directory to analyze")


def _parse_python_file(file_path: Path) -> ast.AST | None:
    """
    Parse a Python file and return its AST.

    Parameters
    ----------
    file_path : Path
        Path to Python file.

    Returns
    -------
    ast.AST | None
        AST if parsing succeeds, None otherwise.
    """
    try:
        content: str = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except Exception:
        return None


def _find_imports_in_python(file_path: Path, module_filter: str | None = None) -> list[dict[str, Any]]:
    """
    Find imports in a Python file.

    Parameters
    ----------
    file_path : Path
        Path to Python file.
    module_filter : str | None, optional
        Filter by module name.

    Returns
    -------
    list[dict[str, Any]]
        List of import information.
    """
    tree = _parse_python_file(file_path)
    if not tree:
        return []

    imports: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name: str = alias.name
                if module_filter and module_filter not in module_name:
                    continue
                imports.append({
                    "module": module_name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "file": str(file_path),
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if module_filter and module_filter not in node.module:
                    continue
                for alias in node.names:
                    imports.append({
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                        "file": str(file_path),
                    })

    return imports


def _find_definitions_in_python(
    file_path: Path,
    name_pattern: str,
    kind_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Find function/class definitions in a Python file.

    Parameters
    ----------
    file_path : Path
        Path to Python file.
    name_pattern : str
        Pattern to match names.
    kind_filter : str | None, optional
        Filter by kind: "function" or "class".

    Returns
    -------
    list[dict[str, Any]]
        List of definition information.
    """
    tree = _parse_python_file(file_path)
    if not tree:
        return []

    pattern = re.compile(name_pattern)
    definitions: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if kind_filter and kind_filter != "function":
                continue
            if pattern.search(node.name):
                definitions.append({
                    "name": node.name,
                    "kind": "function",
                    "line": node.lineno,
                    "file": str(file_path),
                })
        elif isinstance(node, ast.ClassDef):
            if kind_filter and kind_filter != "class":
                continue
            if pattern.search(node.name):
                definitions.append({
                    "name": node.name,
                    "kind": "class",
                    "line": node.lineno,
                    "file": str(file_path),
                })

    return definitions


def _find_usages_in_python(
    file_path: Path,
    symbol: str,
    exact: bool = True,
) -> list[dict[str, Any]]:
    """
    Find usages of a symbol in a Python file.

    Parameters
    ----------
    file_path : Path
        Path to Python file.
    symbol : str
        Symbol name to find.
    exact : bool, default=True
        Match exact name only.

    Returns
    -------
    list[dict[str, Any]]
        List of usage information.
    """
    try:
        content: str = file_path.read_text(encoding="utf-8")
        lines: list[str] = content.splitlines()
    except Exception:
        return []

    usages: list[dict[str, Any]] = []
    pattern = re.compile(rf"\b{re.escape(symbol)}\b" if exact else symbol)

    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            usages.append({
                "symbol": symbol,
                "line": i,
                "file": str(file_path),
                "context": line.strip()[:80],
            })

    return usages


def _calculate_python_metrics(file_path: Path) -> dict[str, Any]:
    """
    Calculate code metrics for a Python file.

    Parameters
    ----------
    file_path : Path
        Path to Python file.

    Returns
    -------
    dict[str, Any]
        Metrics dictionary.
    """
    try:
        content: str = file_path.read_text(encoding="utf-8")
        lines: list[str] = content.splitlines()
    except Exception:
        return {}

    tree = _parse_python_file(file_path)
    if not tree:
        return {
            "lines": len(lines),
            "functions": 0,
            "classes": 0,
        }

    functions: int = 0
    classes: int = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1

    return {
        "lines": len(lines),
        "functions": functions,
        "classes": classes,
        "file": str(file_path),
    }


@register_tool(name="find_imports", description="Find all imports in codebase")
class FindImportsTool(Tool):
    """
    Tool for finding imports in codebase.

    This tool searches for import statements in Python files and can
    filter by module name or file pattern.

    Attributes
    ----------
    name : str
        Tool name: "find_imports"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[FindImportsParams]
        Parameter schema
    """

    name: str = "find_imports"
    description: str = (
        "Find all imports in the codebase. Supports filtering by module "
        "name and file pattern. Currently supports Python files."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[FindImportsParams] = FindImportsParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the find_imports tool."""
        params = FindImportsParams(**invocation.params)
        search_path: Path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists():
            return ToolResult.error_result(f"Path does not exist: {search_path}")

        imports: list[dict[str, Any]] = []

        if search_path.is_file():
            if search_path.suffix == ".py":
                imports.extend(_find_imports_in_python(search_path, params.module))
        else:
            pattern: str = params.file_pattern or "*.py"
            for py_file in search_path.rglob(pattern):
                if py_file.is_file():
                    imports.extend(_find_imports_in_python(py_file, params.module))

        if not imports:
            return ToolResult.success_result(
                output="No imports found matching the criteria.",
            )

        # Format output
        output_lines: list[str] = []
        for imp in imports:
            if "name" in imp:
                line = f"{imp['file']}:{imp['line']} - from {imp['module']} import {imp['name']}"
                if imp.get("alias"):
                    line += f" as {imp['alias']}"
            else:
                line = f"{imp['file']}:{imp['line']} - import {imp['module']}"
                if imp.get("alias"):
                    line += f" as {imp['alias']}"
            output_lines.append(line)

        return ToolResult.success_result(
            output="\n".join(output_lines),
            metadata={"count": len(imports)},
        )


@register_tool(name="find_definitions", description="Find function/class definitions")
class FindDefinitionsTool(Tool):
    """
    Tool for finding function and class definitions.

    This tool searches for function and class definitions matching
    a name pattern in the codebase.

    Attributes
    ----------
    name : str
        Tool name: "find_definitions"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[FindDefinitionsParams]
        Parameter schema
    """

    name: str = "find_definitions"
    description: str = (
        "Find function and class definitions matching a name pattern. "
        "Supports regex patterns and filtering by kind (function/class)."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[FindDefinitionsParams] = FindDefinitionsParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the find_definitions tool."""
        params = FindDefinitionsParams(**invocation.params)
        search_path: Path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists():
            return ToolResult.error_result(f"Path does not exist: {search_path}")

        definitions: list[dict[str, Any]] = []

        if search_path.is_file():
            if search_path.suffix == ".py":
                definitions.extend(
                    _find_definitions_in_python(
                        search_path,
                        params.name_pattern,
                        params.kind,
                    ),
                )
        else:
            for py_file in search_path.rglob("*.py"):
                if py_file.is_file():
                    definitions.extend(
                        _find_definitions_in_python(
                            py_file,
                            params.name_pattern,
                            params.kind,
                        ),
                    )

        if not definitions:
            return ToolResult.success_result(
                output="No definitions found matching the criteria.",
            )

        # Format output
        output_lines: list[str] = []
        for defn in definitions:
            output_lines.append(
                f"{defn['file']}:{defn['line']} - {defn['kind']} {defn['name']}",
            )

        return ToolResult.success_result(
            output="\n".join(output_lines),
            metadata={"count": len(definitions)},
        )


@register_tool(name="find_usages", description="Find where symbols are used")
class FindUsagesTool(Tool):
    """
    Tool for finding symbol usages.

    This tool searches for usages of a symbol (function, variable, etc.)
    in the codebase.

    Attributes
    ----------
    name : str
        Tool name: "find_usages"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[FindUsagesParams]
        Parameter schema
    """

    name: str = "find_usages"
    description: str = (
        "Find where a symbol is used in the codebase. Supports exact "
        "matching or pattern matching."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[FindUsagesParams] = FindUsagesParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the find_usages tool."""
        params = FindUsagesParams(**invocation.params)
        search_path: Path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists():
            return ToolResult.error_result(f"Path does not exist: {search_path}")

        usages: list[dict[str, Any]] = []

        if search_path.is_file():
            if search_path.suffix == ".py":
                usages.extend(_find_usages_in_python(search_path, params.symbol, params.exact))
        else:
            for py_file in search_path.rglob("*.py"):
                if py_file.is_file():
                    usages.extend(
                        _find_usages_in_python(py_file, params.symbol, params.exact),
                    )

        if not usages:
            return ToolResult.success_result(
                output=f"No usages found for symbol '{params.symbol}'.",
            )

        # Format output
        output_lines: list[str] = []
        for usage in usages:
            output_lines.append(
                f"{usage['file']}:{usage['line']} - {usage['context']}",
            )

        return ToolResult.success_result(
            output="\n".join(output_lines),
            metadata={"count": len(usages), "symbol": params.symbol},
        )


@register_tool(name="code_metrics", description="Calculate code metrics")
class CodeMetricsTool(Tool):
    """
    Tool for calculating code metrics.

    This tool calculates various metrics for files or directories
    including lines of code, function counts, and class counts.

    Attributes
    ----------
    name : str
        Tool name: "code_metrics"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[CodeMetricsParams]
        Parameter schema
    """

    name: str = "code_metrics"
    description: str = (
        "Calculate code metrics for files or directories including "
        "lines of code, function counts, and class counts."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[CodeMetricsParams] = CodeMetricsParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the code_metrics tool."""
        params = CodeMetricsParams(**invocation.params)
        search_path: Path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists():
            return ToolResult.error_result(f"Path does not exist: {search_path}")

        all_metrics: list[dict[str, Any]] = []

        if search_path.is_file():
            if search_path.suffix == ".py":
                metrics = _calculate_python_metrics(search_path)
                if metrics:
                    all_metrics.append(metrics)
        else:
            for py_file in search_path.rglob("*.py"):
                if py_file.is_file():
                    metrics = _calculate_python_metrics(py_file)
                    if metrics:
                        all_metrics.append(metrics)

        if not all_metrics:
            return ToolResult.success_result(
                output="No Python files found to analyze.",
            )

        # Aggregate metrics
        total_lines: int = sum(m.get("lines", 0) for m in all_metrics)
        total_functions: int = sum(m.get("functions", 0) for m in all_metrics)
        total_classes: int = sum(m.get("classes", 0) for m in all_metrics)
        file_count: int = len(all_metrics)

        output_lines: list[str] = [
            f"Code Metrics for: {params.path}",
            f"Files analyzed: {file_count}",
            f"Total lines: {total_lines}",
            f"Total functions: {total_functions}",
            f"Total classes: {total_classes}",
            "",
            "Per-file metrics:",
        ]

        for metrics in sorted(all_metrics, key=lambda x: x.get("file", "")):
            output_lines.append(
                f"  {metrics.get('file', 'unknown')}: "
                f"{metrics.get('lines', 0)} lines, "
                f"{metrics.get('functions', 0)} functions, "
                f"{metrics.get('classes', 0)} classes",
            )

        return ToolResult.success_result(
            output="\n".join(output_lines),
            metadata={
                "file_count": file_count,
                "total_lines": total_lines,
                "total_functions": total_functions,
                "total_classes": total_classes,
            },
        )
