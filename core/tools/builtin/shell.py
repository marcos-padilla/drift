"""
Shell command execution tool.

This module provides a tool for executing shell commands with timeout
support, environment variable filtering, and safety checks.
"""

import asyncio
import fnmatch
import logging
import os
import signal
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolConfirmation, ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)

# Blocked commands for safety
BLOCKED_COMMANDS: set[str] = {
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "fdisk",
    "parted",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777 /",
    "chmod -R 777",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}


class ShellParams(BaseModel):
    """
    Parameters for the shell tool.

    Parameters
    ----------
    command : str
        The shell command to execute.
    timeout : int, default=120
        Timeout in seconds (1-600).
    cwd : str | None, optional
        Working directory for the command.

    Examples
    --------
    >>> params = ShellParams(command="ls -la", timeout=30)
    """

    command: str = Field(..., description="The shell command to execute")
    timeout: int = Field(
        120,
        ge=1,
        le=600,
        description="Timeout in seconds (default: 120)",
    )
    cwd: str | None = Field(None, description="Working directory for the command")


class ShellTool(Tool):
    """
    Tool for executing shell commands.

    This tool executes shell commands with timeout support, environment
    variable filtering, and safety checks for dangerous commands.

    Attributes
    ----------
    name : str
        Tool name: "shell"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: SHELL
    schema : type[ShellParams]
        Parameter schema
    """

    name: str = "shell"
    kind: ToolKind = ToolKind.SHELL
    description: str = (
        "Execute a shell command. Use this for running system commands, "
        "scripts and CLI tools."
    )
    schema: type[ShellParams] = ShellParams

    async def get_confirmation(
        self,
        invocation: ToolInvocation,
    ) -> ToolConfirmation | None:
        """
        Get confirmation request for shell command execution.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation context.

        Returns
        -------
        ToolConfirmation | None
            Confirmation request with command details.
        """
        params = ShellParams(**invocation.params)

        for blocked in BLOCKED_COMMANDS:
            if blocked in params.command:
                return ToolConfirmation(
                    tool_name=self.name,
                    params=invocation.params,
                    description=f"Execute (BLOCKED): {params.command}",
                    command=params.command,
                    is_dangerous=True,
                )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Execute: {params.command}",
            command=params.command,
            is_dangerous=False,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the shell command.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters and working directory.

        Returns
        -------
        ToolResult
            Result containing command output and exit code.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = ShellParams(**invocation.params)

        command: str = params.command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult.error_result(
                    f"Command blocked for safety: {params.command}",
                    metadata={"blocked": True},
                )

        if params.cwd:
            cwd: Path = Path(params.cwd)
            if not cwd.is_absolute():
                cwd = invocation.cwd / cwd
        else:
            cwd = invocation.cwd

        if not cwd.exists():
            return ToolResult.error_result(f"Working directory doesn't exist: {cwd}")

        env: dict[str, str] = self._build_environment()
        if sys.platform == "win32":
            shell_cmd: list[str] = ["cmd.exe", "/c", params.command]
        else:
            shell_cmd = ["/bin/bash", "-c", params.command]

        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )

        try:
            stdout_data: bytes
            stderr_data: bytes
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=params.timeout,
            )
        except asyncio.TimeoutError:
            if sys.platform != "win32":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
            await process.wait()
            return ToolResult.error_result(
                f"Command timed out after {params.timeout}s",
            )

        stdout: str = stdout_data.decode("utf-8", errors="replace")
        stderr: str = stderr_data.decode("utf-8", errors="replace")
        exit_code: int | None = process.returncode

        output: str = ""
        if stdout.strip():
            output += stdout.rstrip()

        if stderr.strip():
            output += "\n--- stderr ---\n"
            output += stderr.rstrip()

        if exit_code != 0:
            output += f"\nExit code: {exit_code}"

        if len(output) > 100 * 1024:
            output = output[: 100 * 1024] + "\n... [output truncated]"

        return ToolResult(
            success=exit_code == 0,
            output=output,
            error=stderr if exit_code != 0 else None,
            exit_code=exit_code,
        )

    def _build_environment(self) -> dict[str, str]:
        """
        Build environment variables for command execution.

        Filters out sensitive environment variables based on configuration
        and adds any explicitly set variables.

        Returns
        -------
        dict[str, str]
            Environment variables dictionary.
        """
        env: dict[str, str] = os.environ.copy()

        shell_environment = self.config.shell_environment

        if not shell_environment.ignore_default_excludes:
            for pattern in shell_environment.exclude_patterns:
                keys_to_remove: list[str] = [
                    k
                    for k in env.keys()
                    if fnmatch.fnmatch(k.upper(), pattern.upper())
                ]

                for k in keys_to_remove:
                    del env[k]

        if shell_environment.set_vars:
            env.update(shell_environment.set_vars)

        return env
