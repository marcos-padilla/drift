"""
Dependency management tools for listing and checking dependencies.

This module provides tools for managing project dependencies including
listing dependencies and checking for updates.
"""

import json
import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.tools.registration.decorator import register_tool
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class ListDependenciesParams(BaseModel):
    """
    Parameters for the list_dependencies tool.

    Parameters
    ----------
    path : str | None, optional
        Project path (defaults to current directory).

    Examples
    --------
    >>> params = ListDependenciesParams(path=".")
    """

    path: str | None = Field(
        None,
        description="Project path (defaults to current directory)",
    )


class CheckUpdatesParams(BaseModel):
    """
    Parameters for the check_updates tool.

    Parameters
    ----------
    path : str | None, optional
        Project path (defaults to current directory).
    outdated_only : bool, default=True
        Show only outdated packages.

    Examples
    --------
    >>> params = CheckUpdatesParams(path=".", outdated_only=True)
    """

    path: str | None = Field(
        None,
        description="Project path (defaults to current directory)",
    )
    outdated_only: bool = Field(
        True,
        description="Show only outdated packages (default: True)",
    )


def _parse_python_dependencies(cwd: Path) -> dict[str, str] | None:
    """
    Parse Python dependencies from requirements.txt or pyproject.toml.

    Parameters
    ----------
    cwd : Path
        Project directory.

    Returns
    -------
    dict[str, str] | None
        Dictionary of package names to versions, or None if not found.
    """
    # Try requirements.txt first
    req_file = cwd / "requirements.txt"
    if req_file.exists():
        deps: dict[str, str] = {}
        try:
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Parse "package==version" or "package>=version"
                parts = line.split("==")
                if len(parts) == 2:
                    deps[parts[0].strip()] = parts[1].strip()
                else:
                    parts = line.split(">=")
                    if len(parts) == 2:
                        deps[parts[0].strip()] = parts[1].strip()
                    else:
                        deps[line.split()[0]] = "unknown"
            return deps
        except Exception:
            pass

    # Try pyproject.toml
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomli

            data = tomli.loads(pyproject.read_text())
            deps = {}
            if "project" in data and "dependencies" in data["project"]:
                for dep in data["project"]["dependencies"]:
                    parts = dep.split("==")
                    if len(parts) == 2:
                        deps[parts[0].strip()] = parts[1].strip()
                    else:
                        deps[dep.split()[0]] = "unknown"
            return deps
        except Exception:
            pass

    return None


def _parse_node_dependencies(cwd: Path) -> dict[str, str] | None:
    """
    Parse Node.js dependencies from package.json.

    Parameters
    ----------
    cwd : Path
        Project directory.

    Returns
    -------
    dict[str, str] | None
        Dictionary of package names to versions, or None if not found.
    """
    pkg_file = cwd / "package.json"
    if not pkg_file.exists():
        return None

    try:
        data = json.loads(pkg_file.read_text())
        deps: dict[str, str] = {}
        deps.update(data.get("dependencies", {}))
        deps.update(data.get("devDependencies", {}))
        return deps
    except Exception:
        return None


@register_tool(name="list_dependencies", description="List project dependencies")
class ListDependenciesTool(Tool):
    """
    Tool for listing project dependencies.

    This tool parses and displays dependencies from package files
    (requirements.txt, package.json, etc.).

    Attributes
    ----------
    name : str
        Tool name: "list_dependencies"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[ListDependenciesParams]
        Parameter schema
    """

    name: str = "list_dependencies"
    description: str = (
        "List all project dependencies from package files. "
        "Supports Python (requirements.txt, pyproject.toml) and Node.js (package.json)."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[ListDependenciesParams] = ListDependenciesParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the list_dependencies tool."""
        params = ListDependenciesParams(**invocation.params)
        project_path: Path = (
            resolve_path(invocation.cwd, params.path)
            if params.path
            else invocation.cwd
        )

        if not project_path.exists():
            return ToolResult.error_result(f"Path does not exist: {project_path}")

        if not project_path.is_dir():
            return ToolResult.error_result(f"Path is not a directory: {project_path}")

        # Try Python dependencies
        py_deps = _parse_python_dependencies(project_path)
        if py_deps:
            output_lines: list[str] = ["Python Dependencies:"]
            for pkg, version in sorted(py_deps.items()):
                output_lines.append(f"  {pkg}: {version}")
            return ToolResult.success_result(
                output="\n".join(output_lines),
                metadata={"type": "python", "count": len(py_deps)},
            )

        # Try Node.js dependencies
        node_deps = _parse_node_dependencies(project_path)
        if node_deps:
            output_lines = ["Node.js Dependencies:"]
            for pkg, version in sorted(node_deps.items()):
                output_lines.append(f"  {pkg}: {version}")
            return ToolResult.success_result(
                output="\n".join(output_lines),
                metadata={"type": "nodejs", "count": len(node_deps)},
            )

        return ToolResult.error_result(
            "No dependency file found (requirements.txt, pyproject.toml, or package.json)",
        )


@register_tool(name="check_updates", description="Check for dependency updates")
class CheckUpdatesTool(Tool):
    """
    Tool for checking dependency updates.

    This tool checks for outdated packages and security vulnerabilities.

    Attributes
    ----------
    name : str
        Tool name: "check_updates"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: READ
    schema : type[CheckUpdatesParams]
        Parameter schema
    """

    name: str = "check_updates"
    description: str = (
        "Check for outdated dependencies and security vulnerabilities. "
        "Supports Python (pip list --outdated) and Node.js (npm outdated)."
    )
    kind: ToolKind = ToolKind.READ
    schema: type[CheckUpdatesParams] = CheckUpdatesParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the check_updates tool."""
        params = CheckUpdatesParams(**invocation.params)
        project_path: Path = (
            resolve_path(invocation.cwd, params.path)
            if params.path
            else invocation.cwd
        )

        if not project_path.exists():
            return ToolResult.error_result(f"Path does not exist: {project_path}")

        if not project_path.is_dir():
            return ToolResult.error_result(f"Path is not a directory: {project_path}")

        # Check Python dependencies
        if (project_path / "requirements.txt").exists() or (
            project_path / "pyproject.toml"
        ).exists():
            try:
                result = subprocess.run(
                    ["pip", "list", "--outdated"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    output: str = result.stdout
                    if not output or "Package" not in output:
                        output = "All packages are up to date."
                    return ToolResult.success_result(
                        output=output,
                        metadata={"type": "python"},
                    )
                else:
                    return ToolResult.error_result(
                        f"Failed to check updates: {result.stderr}",
                    )
            except FileNotFoundError:
                return ToolResult.error_result("pip not found. Please install pip.")
            except subprocess.TimeoutExpired:
                return ToolResult.error_result("Update check timed out")
            except Exception as e:
                logger.exception(f"Failed to check Python updates: {e}")
                return ToolResult.error_result(f"Failed to check updates: {e}")

        # Check Node.js dependencies
        if (project_path / "package.json").exists():
            try:
                result = subprocess.run(
                    ["npm", "outdated"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # npm outdated returns exit code 1 if there are outdated packages
                output = result.stdout
                if result.returncode == 1:
                    if not output:
                        output = "Some packages are outdated."
                elif result.returncode == 0:
                    output = "All packages are up to date."
                else:
                    return ToolResult.error_result(
                        f"Failed to check updates: {result.stderr}",
                    )

                return ToolResult.success_result(
                    output=output,
                    metadata={"type": "nodejs"},
                )
            except FileNotFoundError:
                return ToolResult.error_result("npm not found. Please install npm.")
            except subprocess.TimeoutExpired:
                return ToolResult.error_result("Update check timed out")
            except Exception as e:
                logger.exception(f"Failed to check Node.js updates: {e}")
                return ToolResult.error_result(f"Failed to check updates: {e}")

        return ToolResult.error_result(
            "No dependency file found (requirements.txt, pyproject.toml, or package.json)",
        )
