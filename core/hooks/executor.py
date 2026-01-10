"""
Hook execution logic.

This module provides functionality to execute hooks with proper
timeout handling and error management.
"""

import asyncio
import logging
import os
import signal
import sys
import tempfile
from pathlib import Path
from typing import Any

from core.config.schema import HookConfig

logger = logging.getLogger(__name__)


async def execute_hook(
    hook: HookConfig,
    env: dict[str, str],
    cwd: Path,
) -> None:
    """
    Execute a hook command or script.

    Parameters
    ----------
    hook : HookConfig
        Hook configuration.
    env : dict[str, str]
        Environment variables for execution.
    cwd : Path
        Working directory for execution.

    Raises
    ------
    Exception
        If hook execution fails.

    Examples
    --------
    >>> await execute_hook(hook_config, env_vars, Path.cwd())
    """
    try:
        if hook.command:
            await _run_command(hook.command, hook.timeout_sec, env, cwd)
        elif hook.script:
            script_path: Path = await _create_script_file(hook.script)
            try:
                await _run_command(str(script_path), hook.timeout_sec, env, cwd)
            finally:
                script_path.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Hook '{hook.name}' failed: {e}", exc_info=True)
        # Don't raise - hooks should not break the main flow


async def _create_script_file(script_content: str) -> Path:
    """
    Create a temporary script file from script content.

    Parameters
    ----------
    script_content : str
        Script content to write.

    Returns
    -------
    Path
        Path to the created script file.

    Examples
    --------
    >>> script_path = await _create_script_file("#!/bin/bash\\necho 'hello'")
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".sh",
        delete=False,
    ) as f:
        f.write("#!/bin/bash\n")
        f.write(script_content)
        script_path = Path(f.name)

    os.chmod(script_path, 0o755)
    return script_path


async def _run_command(
    command: str,
    timeout: float,
    env: dict[str, str],
    cwd: Path,
) -> None:
    """
    Run a shell command with timeout.

    Parameters
    ----------
    command : str
        Command to execute.
    timeout : float
        Timeout in seconds.
    env : dict[str, str]
        Environment variables.
    cwd : Path
        Working directory.

    Raises
    ------
    asyncio.TimeoutError
        If command exceeds timeout.

    Examples
    --------
    >>> await _run_command("echo hello", 10.0, {}, Path.cwd())
    """
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
        start_new_session=True,
    )

    try:
        await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        if sys.platform != "win32":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
        await process.wait()
        raise
