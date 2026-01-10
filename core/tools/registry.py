"""
Tool registry for managing and invoking tools.

This module provides functionality to register, discover, and invoke tools
with proper validation, approval checking, and hook integration.
"""

import logging
from pathlib import Path
from typing import Any

from core.config.schema import Configuration
from core.hooks.system import HookSystem
from core.safety.approval import ApprovalContext, ApprovalDecision, ApprovalManager
from core.safety.models import ToolConfirmation
from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing and invoking tools.

    This class maintains a collection of available tools and provides
    methods to register, retrieve, and invoke them with proper validation,
    approval checking, and hook integration.

    Parameters
    ----------
    config : Configuration
        Configuration object with tool settings.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    _tools : dict[str, Tool]
        Dictionary of registered tools keyed by name.
    _mcp_tools : dict[str, Tool]
        Dictionary of MCP tools keyed by name.

    Examples
    --------
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> registry = ToolRegistry(config)
    >>> registry.register(MyTool(config))
    >>> tool = registry.get("my_tool")
    >>> result = await registry.invoke("my_tool", {"param": "value"}, Path.cwd(), hooks, approval)
    """

    def __init__(self, config: Configuration) -> None:
        self.config: Configuration = config
        self._tools: dict[str, Tool] = {}
        self._mcp_tools: dict[str, Tool] = {}

    @property
    def connected_mcp_servers(self) -> list[Tool]:
        """
        Get list of tools from connected MCP servers.

        Returns
        -------
        list[Tool]
            List of MCP tools.
        """
        return list(self._mcp_tools.values())

    def register(self, tool: Tool) -> None:
        """
        Register a tool in the registry.

        Parameters
        ----------
        tool : Tool
            Tool instance to register.

        Examples
        --------
        >>> registry.register(MyTool(config))
        """
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_mcp_tool(self, tool: Tool) -> None:
        """
        Register an MCP tool in the registry.

        Parameters
        ----------
        tool : Tool
            MCP tool instance to register.

        Examples
        --------
        >>> registry.register_mcp_tool(mcp_tool)
        """
        self._mcp_tools[tool.name] = tool
        logger.debug(f"Registered MCP tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool from the registry.

        Parameters
        ----------
        name : str
            Name of the tool to unregister.

        Returns
        -------
        bool
            True if tool was found and removed, False otherwise.

        Examples
        --------
        >>> success = registry.unregister("my_tool")
        """
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True

        return False

    def get(self, name: str) -> Tool | None:
        """
        Get a tool by name.

        Parameters
        ----------
        name : str
            Name of the tool to retrieve.

        Returns
        -------
        Tool | None
            Tool instance if found, None otherwise.

        Examples
        --------
        >>> tool = registry.get("read_file")
        >>> if tool:
        ...     result = await tool.execute(invocation)
        """
        if name in self._tools:
            return self._tools[name]
        elif name in self._mcp_tools:
            return self._mcp_tools[name]

        return None

    def get_tools(self) -> list[Tool]:
        """
        Get all available tools, optionally filtered by allowed_tools config.

        Returns
        -------
        list[Tool]
            List of all available tools (filtered if allowed_tools is set).

        Examples
        --------
        >>> tools = registry.get_tools()
        >>> for tool in tools:
        ...     print(tool.name)
        """
        tools: list[Tool] = []

        for tool in self._tools.values():
            tools.append(tool)

        for mcp_tool in self._mcp_tools.values():
            tools.append(mcp_tool)

        if self.config.allowed_tools:
            allowed_set = set(self.config.allowed_tools)
            tools = [t for t in tools if t.name in allowed_set]

        return tools

    def get_schemas(self) -> list[dict[str, Any]]:
        """
        Get OpenAI-compatible schemas for all tools.

        Returns
        -------
        list[dict[str, Any]]
            List of tool schemas in OpenAI format.

        Examples
        --------
        >>> schemas = registry.get_schemas()
        >>> # Use with LLM client
        """
        return [tool.to_openai_schema() for tool in self.get_tools()]

    async def invoke(
        self,
        name: str,
        params: dict[str, Any],
        cwd: Path,
        hook_system: HookSystem,
        approval_manager: ApprovalManager | None = None,
    ) -> ToolResult:
        """
        Invoke a tool with validation, approval checking, and hooks.

        Parameters
        ----------
        name : str
            Name of the tool to invoke.
        params : dict[str, Any]
            Parameters for the tool.
        cwd : Path
            Current working directory.
        hook_system : HookSystem
            Hook system for triggering hooks.
        approval_manager : ApprovalManager | None, optional
            Approval manager for safety checking.

        Returns
        -------
        ToolResult
            Result of the tool execution.

        Examples
        --------
        >>> result = await registry.invoke(
        ...     "write_file",
        ...     {"path": "test.py", "content": "print('hello')"},
        ...     Path.cwd(),
        ...     hook_system,
        ...     approval_manager
        ... )
        """
        tool = self.get(name)
        if tool is None:
            result = ToolResult.error_result(
                f"Unknown tool: {name}",
                metadata={"tool_name": name},
            )
            await hook_system.trigger_after_tool(name, params, result)
            return result

        validation_errors = tool.validate_params(params)
        if validation_errors:
            result = ToolResult.error_result(
                f"Invalid parameters: {'; '.join(validation_errors)}",
                metadata={
                    "tool_name": name,
                    "validation_errors": validation_errors,
                },
            )

            await hook_system.trigger_after_tool(name, params, result)

            return result

        await hook_system.trigger_before_tool(name, params)
        invocation = ToolInvocation(
            params=params,
            cwd=cwd,
        )

        if approval_manager:
            confirmation = await tool.get_confirmation(invocation)
            if confirmation:
                context = ApprovalContext(
                    tool_name=name,
                    params=params,
                    is_mutating=tool.is_mutating(params),
                    affected_paths=confirmation.affected_paths,
                    command=confirmation.command,
                    is_dangerous=confirmation.is_dangerous,
                )

                decision = await approval_manager.check_approval(context)
                if decision == ApprovalDecision.REJECTED:
                    result = ToolResult.error_result(
                        "Operation rejected by safety policy",
                    )
                    await hook_system.trigger_after_tool(name, params, result)
                    return result
                elif decision == ApprovalDecision.NEEDS_CONFIRMATION:
                    tool_confirmation = ToolConfirmation(
                        tool_name=name,
                        description=confirmation.description,
                        context=context,
                    )
                    approved = await approval_manager.request_confirmation(
                        tool_confirmation,
                    )

                    if not approved:
                        result = ToolResult.error_result(
                            "User rejected the operation",
                        )
                        await hook_system.trigger_after_tool(name, params, result)
                        return result

        try:
            result = await tool.execute(invocation)
        except Exception as e:
            logger.exception(f"Tool {name} raised unexpected error")
            result = ToolResult.error_result(
                f"Internal error: {str(e)}",
                metadata={
                    "tool_name": name,
                },
            )

        await hook_system.trigger_after_tool(name, params, result)
        return result
