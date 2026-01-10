"""
Code quality tools for formatting, linting, and type checking.

This module provides tools for running code formatters, linters, and
type checkers on codebases.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.tools.registration.decorator import register_tool
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class FormatCodeParams(BaseModel):
    """
    Parameters for the format_code tool.

    Parameters
    ----------
    path : str
        File or directory to format.
    language : str | None, optional
        Language (auto-detected if not provided): "python", "javascript", "typescript".

    Examples
    --------
    >>> params = FormatCodeParams(path="src/", language="python")
    """

    path: str = Field(..., description="File or directory to format")
    language: str | None = Field(
        None,
        description="Language (auto-detected if not provided)",
    )


class LintCodeParams(BaseModel):
    """
    Parameters for the lint_code tool.

    Parameters
    ----------
    path : str
        File or directory to lint.
    language : str | None, optional
        Language (auto-detected if not provided).

    Examples
    --------
    >>> params = LintCodeParams(path="src/", language="python")
    """

    path: str = Field(..., description="File or directory to lint")
    language: str | None = Field(
        None,
        description="Language (auto-detected if not provided)",
    )


class TypeCheckParams(BaseModel):
    """
    Parameters for the type_check tool.

    Parameters
    ----------
    path : str
        File or directory to type check.
    language : str | None, optional
        Language (auto-detected if not provided): "python", "typescript".

    Examples
    --------
    >>> params = TypeCheckParams(path="src/", language="python")
    """

    path: str = Field(..., description="File or directory to type check")
    language: str | None = Field(
        None,
        description="Language (auto-detected if not provided)",
    )


def _detect_language(path: Path) -> str | None:
    """
    Detect programming language from file extension.

    Parameters
    ----------
    path : Path
        File or directory path.

    Returns
    -------
    str | None
        Detected language or None.
    """
    if path.is_file():
        ext = path.suffix.lower()
        if ext == ".py":
            return "python"
        elif ext in {".js", ".jsx"}:
            return "javascript"
        elif ext in {".ts", ".tsx"}:
            return "typescript"
    elif path.is_dir():
        # Check for common files
        if (path / "pyproject.toml").exists() or (path / "setup.py").exists():
            return "python"
        elif (path / "package.json").exists():
            return "javascript"  # Could be JS or TS
    return None


@register_tool(name="format_code", description="Format code files")
class FormatCodeTool(Tool):
    """
    Tool for formatting code files.

    This tool runs language-specific formatters (black for Python,
    prettier for JS/TS, etc.).

    Attributes
    ----------
    name : str
        Tool name: "format_code"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: WRITE
    schema : type[FormatCodeParams]
        Parameter schema
    """

    name: str = "format_code"
    description: str = (
        "Format code files using language-specific formatters. "
        "Supports Python (black), JavaScript/TypeScript (prettier), etc."
    )
    kind: ToolKind = ToolKind.WRITE
    schema: type[FormatCodeParams] = FormatCodeParams

    def __init__(self, config) -> None:
        super().__init__(config)

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if this operation modifies files."""
        return True

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the format_code tool."""
        params = FormatCodeParams(**invocation.params)
        target_path: Path = resolve_path(invocation.cwd, params.path)

        if not target_path.exists():
            return ToolResult.error_result(f"Path does not exist: {params.path}")

        language: str | None = params.language or _detect_language(target_path)
        if not language:
            return ToolResult.error_result(
                "Could not detect language. Please specify language parameter.",
            )

        try:
            if language == "python":
                # Try black first, then autopep8
                cmd: list[str] = ["black", str(target_path)]
                result = subprocess.run(
                    cmd,
                    cwd=invocation.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    # Try autopep8 as fallback
                    cmd = ["autopep8", "--in-place", "--recursive", str(target_path)]
                    result = subprocess.run(
                        cmd,
                        cwd=invocation.cwd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Formatting failed: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output=f"Formatted {params.path} using {language} formatter",
                    metadata={"language": language, "formatter": "black/autopep8"},
                )

            elif language in {"javascript", "typescript"}:
                # Try prettier
                cmd = ["npx", "--yes", "prettier", "--write", str(target_path)]
                result = subprocess.run(
                    cmd,
                    cwd=invocation.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    return ToolResult.error_result(
                        f"Formatting failed: {result.stderr}",
                        output=result.stdout,
                    )

                return ToolResult.success_result(
                    output=f"Formatted {params.path} using prettier",
                    metadata={"language": language, "formatter": "prettier"},
                )

            else:
                return ToolResult.error_result(
                    f"Unsupported language for formatting: {language}",
                )

        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Formatting command timed out")
        except FileNotFoundError:
            return ToolResult.error_result(
                f"Formatter not found. Please install formatter for {language}.",
            )
        except Exception as e:
            logger.exception(f"Failed to format code: {e}")
            return ToolResult.error_result(f"Failed to format code: {e}")


@register_tool(name="lint_code", description="Lint code files")
class LintCodeTool(Tool):
    """
    Tool for linting code files.

    This tool runs language-specific linters (ruff/flake8 for Python,
    eslint for JS/TS, etc.).

    Attributes
    ----------
    name : str
        Tool name: "lint_code"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[LintCodeParams]
        Parameter schema
    """

    name: str = "lint_code"
    description: str = (
        "Lint code files using language-specific linters. "
        "Supports Python (ruff, flake8), JavaScript/TypeScript (eslint), etc."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[LintCodeParams] = LintCodeParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the lint_code tool."""
        params = LintCodeParams(**invocation.params)
        target_path: Path = resolve_path(invocation.cwd, params.path)

        if not target_path.exists():
            return ToolResult.error_result(f"Path does not exist: {params.path}")

        language: str | None = params.language or _detect_language(target_path)
        if not language:
            return ToolResult.error_result(
                "Could not detect language. Please specify language parameter.",
            )

        try:
            if language == "python":
                # Try ruff first, then flake8
                cmd: list[str] = ["ruff", "check", str(target_path)]
                result = subprocess.run(
                    cmd,
                    cwd=invocation.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0 and "not found" in result.stderr.lower():
                    # Try flake8 as fallback
                    cmd = ["flake8", str(target_path)]
                    result = subprocess.run(
                        cmd,
                        cwd=invocation.cwd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                output: str = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"

                # Exit code 0 means no issues, non-zero means issues found
                success: bool = result.returncode == 0
                if success and not output:
                    output = "No linting issues found."

                return ToolResult.success_result(
                    output=output,
                    metadata={
                        "language": language,
                        "linter": "ruff/flake8",
                        "issues_found": result.returncode != 0,
                    },
                )

            elif language in {"javascript", "typescript"}:
                # Try eslint
                cmd = ["npx", "--yes", "eslint", str(target_path)]
                result = subprocess.run(
                    cmd,
                    cwd=invocation.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                output = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"

                success = result.returncode == 0
                if success and not output:
                    output = "No linting issues found."

                return ToolResult.success_result(
                    output=output,
                    metadata={
                        "language": language,
                        "linter": "eslint",
                        "issues_found": result.returncode != 0,
                    },
                )

            else:
                return ToolResult.error_result(
                    f"Unsupported language for linting: {language}",
                )

        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Linting command timed out")
        except FileNotFoundError:
            return ToolResult.error_result(
                f"Linter not found. Please install linter for {language}.",
            )
        except Exception as e:
            logger.exception(f"Failed to lint code: {e}")
            return ToolResult.error_result(f"Failed to lint code: {e}")


@register_tool(name="type_check", description="Type check code files")
class TypeCheckTool(Tool):
    """
    Tool for type checking code files.

    This tool runs type checkers (mypy for Python, tsc for TypeScript).

    Attributes
    ----------
    name : str
        Tool name: "type_check"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[TypeCheckParams]
        Parameter schema
    """

    name: str = "type_check"
    description: str = (
        "Type check code files using language-specific type checkers. "
        "Supports Python (mypy), TypeScript (tsc), etc."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[TypeCheckParams] = TypeCheckParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the type_check tool."""
        params = TypeCheckParams(**invocation.params)
        target_path: Path = resolve_path(invocation.cwd, params.path)

        if not target_path.exists():
            return ToolResult.error_result(f"Path does not exist: {params.path}")

        language: str | None = params.language or _detect_language(target_path)
        if not language:
            return ToolResult.error_result(
                "Could not detect language. Please specify language parameter.",
            )

        try:
            if language == "python":
                # Use mypy
                cmd: list[str] = ["mypy", str(target_path)]
                result = subprocess.run(
                    cmd,
                    cwd=invocation.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                output: str = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"

                # Exit code 0 means no issues
                success: bool = result.returncode == 0
                if success and not output:
                    output = "No type errors found."

                return ToolResult.success_result(
                    output=output,
                    metadata={
                        "language": language,
                        "checker": "mypy",
                        "errors_found": result.returncode != 0,
                    },
                )

            elif language == "typescript":
                # Use tsc
                cmd = ["npx", "--yes", "tsc", "--noEmit", str(target_path)]
                result = subprocess.run(
                    cmd,
                    cwd=invocation.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                output = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"

                success = result.returncode == 0
                if success and not output:
                    output = "No type errors found."

                return ToolResult.success_result(
                    output=output,
                    metadata={
                        "language": language,
                        "checker": "tsc",
                        "errors_found": result.returncode != 0,
                    },
                )

            else:
                return ToolResult.error_result(
                    f"Unsupported language for type checking: {language}",
                )

        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Type checking command timed out")
        except FileNotFoundError:
            return ToolResult.error_result(
                f"Type checker not found. Please install type checker for {language}.",
            )
        except Exception as e:
            logger.exception(f"Failed to type check code: {e}")
            return ToolResult.error_result(f"Failed to type check code: {e}")
