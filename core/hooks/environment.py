"""
Environment variable building for hook execution.

This module provides functionality to build environment variables
for hook execution with context information.
"""

import json
import os
from typing import Any

from core.config.schema import Configuration, HookTrigger
from core.tools.models import ToolResult

# Environment variable prefixes
ENV_PREFIX: str = "AI_AGENT_"


def build_hook_environment(
    config: Configuration,
    trigger: HookTrigger,
    tool_name: str | None = None,
    tool_params: dict[str, Any] | None = None,
    tool_result: ToolResult | None = None,
    user_message: str | None = None,
    agent_response: str | None = None,
    error: Exception | None = None,
) -> dict[str, str]:
    """
    Build environment variables for hook execution.

    Parameters
    ----------
    config : Configuration
        Configuration object.
    trigger : HookTrigger
        Trigger that caused the hook.
    tool_name : str | None, optional
        Name of the tool if applicable.
    tool_params : dict[str, Any] | None, optional
        Tool parameters if applicable.
    tool_result : ToolResult | None, optional
        Tool result if applicable.
    user_message : str | None, optional
        User message if applicable.
    agent_response : str | None, optional
        Agent response if applicable.
    error : Exception | None, optional
        Error if applicable.

    Returns
    -------
    dict[str, str]
        Environment variables dictionary.

    Examples
    --------
    >>> env = build_hook_environment(
    ...     config,
    ...     HookTrigger.BEFORE_TOOL,
    ...     tool_name="write_file"
    ... )
    """
    env: dict[str, str] = os.environ.copy()
    env[f"{ENV_PREFIX}TRIGGER"] = trigger.value
    env[f"{ENV_PREFIX}CWD"] = str(config.cwd)

    if tool_name:
        env[f"{ENV_PREFIX}TOOL_NAME"] = tool_name

    if tool_params:
        env[f"{ENV_PREFIX}TOOL_PARAMS"] = json.dumps(tool_params)

    if tool_result:
        env[f"{ENV_PREFIX}TOOL_RESULT"] = tool_result.to_model_output()

    if user_message:
        env[f"{ENV_PREFIX}USER_MESSAGE"] = user_message

    if agent_response:
        env[f"{ENV_PREFIX}AGENT_RESPONSE"] = agent_response

    if error:
        env[f"{ENV_PREFIX}ERROR"] = str(error)

    return env
