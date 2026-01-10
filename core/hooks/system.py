"""
Hook system for executing hooks at various trigger points.

This module provides the main HookSystem class that manages hook
execution at different points in the agent lifecycle.
"""

import logging
from typing import Any

from core.config.schema import Configuration, HookTrigger
from core.hooks.environment import build_hook_environment
from core.hooks.executor import execute_hook
from core.tools.models import ToolResult

logger = logging.getLogger(__name__)


class HookSystem:
    """
    System for managing and executing hooks.

    This class manages hook execution at various trigger points including
    before/after agent execution, before/after tool calls, and on errors.

    Parameters
    ----------
    config : Configuration
        Configuration object with hook settings.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    hooks : list[HookConfig]
        List of enabled hooks.

    Examples
    --------
    >>> hook_system = HookSystem(config)
    >>> await hook_system.trigger_before_agent("Hello!")
    >>> await hook_system.trigger_after_tool("read_file", {}, result)
    """

    def __init__(self, config: Configuration) -> None:
        self.config: Configuration = config
        self.hooks: list = []
        if self.config.hooks_enabled:
            self.hooks = [hook for hook in self.config.hooks if hook.enabled]
            logger.debug(f"Initialized hook system with {len(self.hooks)} hooks")

    async def trigger_before_agent(self, user_message: str) -> None:
        """
        Trigger hooks before agent execution.

        Parameters
        ----------
        user_message : str
            User message that will be processed.

        Examples
        --------
        >>> await hook_system.trigger_before_agent("Fix the bug")
        """
        env = build_hook_environment(
            self.config,
            HookTrigger.BEFORE_AGENT,
            user_message=user_message,
        )

        for hook in self.hooks:
            if hook.trigger == HookTrigger.BEFORE_AGENT:
                await execute_hook(hook, env, self.config.cwd)

    async def trigger_after_agent(
        self,
        user_message: str,
        agent_response: str,
    ) -> None:
        """
        Trigger hooks after agent execution.

        Parameters
        ----------
        user_message : str
            Original user message.
        agent_response : str
            Agent's response.

        Examples
        --------
        >>> await hook_system.trigger_after_agent("Fix the bug", "Fixed!")
        """
        env = build_hook_environment(
            self.config,
            HookTrigger.AFTER_AGENT,
            user_message=user_message,
            agent_response=agent_response,
        )

        for hook in self.hooks:
            if hook.trigger == HookTrigger.AFTER_AGENT:
                await execute_hook(hook, env, self.config.cwd)

    async def trigger_before_tool(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
    ) -> None:
        """
        Trigger hooks before tool execution.

        Parameters
        ----------
        tool_name : str
            Name of the tool being called.
        tool_params : dict[str, Any]
            Parameters for the tool.

        Examples
        --------
        >>> await hook_system.trigger_before_tool("write_file", {"path": "test.py"})
        """
        env = build_hook_environment(
            self.config,
            HookTrigger.BEFORE_TOOL,
            tool_name=tool_name,
            tool_params=tool_params,
        )

        for hook in self.hooks:
            if hook.trigger == HookTrigger.BEFORE_TOOL:
                await execute_hook(hook, env, self.config.cwd)

    async def trigger_after_tool(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        tool_result: ToolResult,
    ) -> None:
        """
        Trigger hooks after tool execution.

        Parameters
        ----------
        tool_name : str
            Name of the tool that was called.
        tool_params : dict[str, Any]
            Parameters that were used.
        tool_result : ToolResult
            Result from tool execution.

        Examples
        --------
        >>> await hook_system.trigger_after_tool("write_file", {}, result)
        """
        env = build_hook_environment(
            self.config,
            HookTrigger.AFTER_TOOL,
            tool_name=tool_name,
            tool_params=tool_params,
            tool_result=tool_result,
        )

        for hook in self.hooks:
            if hook.trigger == HookTrigger.AFTER_TOOL:
                await execute_hook(hook, env, self.config.cwd)

    async def trigger_on_error(self, error: Exception) -> None:
        """
        Trigger hooks on error.

        Parameters
        ----------
        error : Exception
            Error that occurred.

        Examples
        --------
        >>> await hook_system.trigger_on_error(ValueError("Something went wrong"))
        """
        env = build_hook_environment(
            self.config,
            HookTrigger.ON_ERROR,
            error=error,
        )

        for hook in self.hooks:
            if hook.trigger == HookTrigger.ON_ERROR:
                await execute_hook(hook, env, self.config.cwd)
