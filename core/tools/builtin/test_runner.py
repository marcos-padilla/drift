"""
Test runner tool for executing test suites.

This module provides a tool for running tests with automatic framework
detection and result parsing.
"""

import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.tools.registration.decorator import register_tool
from core.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class RunTestsParams(BaseModel):
    """
    Parameters for the run_tests tool.

    Parameters
    ----------
    path : str | None, optional
        Test file, directory, or pattern to run (defaults to running all tests).
    framework : str | None, optional
        Test framework (auto-detected if not provided): "pytest", "unittest", "jest", "mocha".

    Examples
    --------
    >>> params = RunTestsParams(path="tests/test_main.py", framework="pytest")
    """

    path: str | None = Field(
        None,
        description="Test file, directory, or pattern to run (defaults to all tests)",
    )
    framework: str | None = Field(
        None,
        description="Test framework (auto-detected if not provided)",
    )


def _detect_test_framework(cwd: Path) -> str | None:
    """
    Detect test framework from project files.

    Parameters
    ----------
    cwd : Path
        Project directory.

    Returns
    -------
    str | None
        Detected framework or None.
    """
    # Check for Python frameworks
    if (cwd / "pytest.ini").exists() or (cwd / "pyproject.toml").exists():
        try:
            content = (cwd / "pyproject.toml").read_text()
            if "pytest" in content.lower():
                return "pytest"
        except Exception:
            pass

    # Check for pytest in requirements
    for req_file in ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]:
        req_path = cwd / req_file
        if req_path.exists():
            try:
                content = req_path.read_text()
                if "pytest" in content.lower():
                    return "pytest"
            except Exception:
                pass

    # Check for Node.js frameworks
    if (cwd / "package.json").exists():
        try:
            import json

            pkg = json.loads((cwd / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "jest" in deps:
                return "jest"
            elif "mocha" in deps:
                return "mocha"
        except Exception:
            pass

    # Check for unittest (Python standard library)
    if (cwd / "test").exists() or (cwd / "tests").exists():
        # Check if there are test files
        for test_dir in [cwd / "test", cwd / "tests"]:
            if test_dir.exists():
                for py_file in test_dir.rglob("test_*.py"):
                    return "unittest"  # Likely unittest

    return None


@register_tool(name="run_tests", description="Execute test suites")
class RunTestsTool(Tool):
    """
    Tool for running test suites.

    This tool automatically detects test frameworks and runs tests
    with appropriate commands.

    Attributes
    ----------
    name : str
        Tool name: "run_tests"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: SHELL
    schema : type[RunTestsParams]
        Parameter schema
    """

    name: str = "run_tests"
    description: str = (
        "Run test suites with automatic framework detection. "
        "Supports pytest, unittest, jest, mocha, and others."
    )
    kind: ToolKind = ToolKind.SHELL
    schema: type[RunTestsParams] = RunTestsParams

    def __init__(self, config) -> None:
        super().__init__(config)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the run_tests tool."""
        params = RunTestsParams(**invocation.params)

        # Detect framework
        framework: str | None = params.framework or _detect_test_framework(invocation.cwd)
        if not framework:
            return ToolResult.error_result(
                "Could not detect test framework. Please specify framework parameter.",
            )

        try:
            cmd: list[str] = []

            if framework == "pytest":
                cmd = ["pytest"]
                if params.path:
                    cmd.append(params.path)
                else:
                    cmd.append("tests/")
                cmd.extend(["-v", "--tb=short"])

            elif framework == "unittest":
                cmd = ["python", "-m", "unittest", "discover"]
                if params.path:
                    cmd = ["python", "-m", "unittest", params.path]
                cmd.append("-v")

            elif framework == "jest":
                cmd = ["npm", "test"]
                if params.path:
                    cmd.append(params.path)
                cmd.append("--")

            elif framework == "mocha":
                cmd = ["npx", "mocha"]
                if params.path:
                    cmd.append(params.path)
                else:
                    cmd.append("test/")

            else:
                return ToolResult.error_result(
                    f"Unsupported test framework: {framework}",
                )

            result = subprocess.run(
                cmd,
                cwd=invocation.cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for tests
            )

            output: str = result.stdout
            if result.stderr:
                output += f"\n\nStderr:\n{result.stderr}"

            # Parse results
            success: bool = result.returncode == 0
            if not output:
                output = "Tests completed (no output)"

            return ToolResult.success_result(
                output=output,
                metadata={
                    "framework": framework,
                    "exit_code": result.returncode,
                    "passed": success,
                },
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return ToolResult.error_result("Test execution timed out")
        except FileNotFoundError:
            return ToolResult.error_result(
                f"Test framework '{framework}' not found. Please install it.",
            )
        except Exception as e:
            logger.exception(f"Failed to run tests: {e}")
            return ToolResult.error_result(f"Failed to run tests: {e}")
