"""
MCP tool wrapper for exposing MCP server tools.

This module provides a Tool wrapper that exposes MCP server tools
as regular tools in the tool registry.
"""

import logging
from typing import Any

from core.tools.base import Tool
from core.tools.mcp.client import MCPClient
from core.tools.mcp.models import MCPToolInfo
from core.tools.models import ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


class MCPTool(Tool):
    """
    Tool wrapper for MCP server tools.

    This class wraps an MCP tool and exposes it as a regular tool
    that can be used by the agent.

    Parameters
    ----------
    config : Configuration
        Configuration object.
    client : MCPClient
        MCP client instance.
    tool_info : MCPToolInfo
        Information about the MCP tool.
    name : str
        Full name for this tool (typically server__tool_name).

    Attributes
    ----------
    name : str
        Tool name.
    description : str
        Tool description from MCP server.
    kind : ToolKind
        Tool kind: MCP
    _tool_info : MCPToolInfo
        MCP tool information.
    _client : MCPClient
        MCP client for calling the tool.

    Examples
    --------
    >>> mcp_tool = MCPTool(config, client, tool_info, "server__tool_name")
    >>> result = await mcp_tool.execute(invocation)
    """

    def __init__(
        self,
        config,
        client: MCPClient,
        tool_info: MCPToolInfo,
        name: str,
    ) -> None:
        super().__init__(config)
        self._tool_info: MCPToolInfo = tool_info
        self._client: MCPClient = client
        self.name: str = name
        self.description: str = self._tool_info.description
        self.kind: ToolKind = ToolKind.MCP

    @property
    def schema(self) -> dict[str, Any]:
        """
        Get the parameter schema for this tool.

        Returns
        -------
        dict[str, Any]
            JSON schema dictionary for tool parameters.
        """
        input_schema: dict[str, Any] = self._tool_info.input_schema or {}
        return {
            "type": "object",
            "properties": input_schema.get("properties", {}),
            "required": input_schema.get("required", []),
        }

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """
        Check if the tool operation is mutating.

        MCP tools are considered mutating by default for safety.

        Parameters
        ----------
        params : dict[str, Any]
            Tool parameters (not used).

        Returns
        -------
        bool
            Always True for MCP tools.
        """
        return True

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the MCP tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters.

        Returns
        -------
        ToolResult
            Result from the MCP tool execution.

        Examples
        --------
        >>> result = await mcp_tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        try:
            result = await self._client.call_tool(
                self._tool_info.name,
                invocation.params,
            )
            output: str = result.get("output", "")
            is_error: bool = result.get("is_error", False)

            if is_error:
                return ToolResult.error_result(output)

            return ToolResult.success_result(output)
        except Exception as e:
            logger.exception(
                f"MCP tool '{self.name}' failed: {e}",
            )
            return ToolResult.error_result(f"MCP tool failed: {e}")
