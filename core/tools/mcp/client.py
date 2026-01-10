"""
MCP client for connecting to and interacting with MCP servers.

This module provides functionality to connect to MCP servers via
stdio or HTTP/SSE transports and call their tools.
"""

import logging
import os
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import SSETransport, StdioTransport

from core.config.schema import MCPServerConfig
from core.tools.mcp.models import MCPServerStatus, MCPToolInfo

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for connecting to an MCP server.

    This class manages the connection to a single MCP server and provides
    access to its tools via stdio or HTTP/SSE transports.

    Parameters
    ----------
    name : str
        Name identifier for this MCP server.
    config : MCPServerConfig
        Configuration for the MCP server.
    cwd : Path
        Current working directory for stdio transports.

    Attributes
    ----------
    name : str
        Server name identifier.
    config : MCPServerConfig
        Server configuration.
    cwd : Path
        Current working directory.
    status : MCPServerStatus
        Current connection status.
    _client : Client | None
        Internal FastMCP client instance.
    _tools : dict[str, MCPToolInfo]
        Dictionary of available tools keyed by name.

    Examples
    --------
    >>> client = MCPClient("filesystem", config, Path.cwd())
    >>> await client.connect()
    >>> tools = client.tools
    >>> result = await client.call_tool("read_file", {"path": "test.txt"})
    >>> await client.disconnect()
    """

    def __init__(
        self,
        name: str,
        config: MCPServerConfig,
        cwd: Path,
    ) -> None:
        self.name: str = name
        self.config: MCPServerConfig = config
        self.cwd: Path = cwd
        self.status: MCPServerStatus = MCPServerStatus.DISCONNECTED
        self._client: Client | None = None
        self._tools: dict[str, MCPToolInfo] = {}

    @property
    def tools(self) -> list[MCPToolInfo]:
        """
        Get list of available tools from this server.

        Returns
        -------
        list[MCPToolInfo]
            List of tool information objects.
        """
        return list(self._tools.values())

    def _create_transport(self) -> StdioTransport | SSETransport:
        """
        Create the appropriate transport for the server.

        Returns
        -------
        StdioTransport | SSETransport
            Transport instance based on configuration.

        Raises
        ------
        ValueError
            If transport configuration is invalid.
        """
        if self.config.command:
            env: dict[str, str] = os.environ.copy()
            env.update(self.config.env)

            return StdioTransport(
                command=self.config.command,
                args=list(self.config.args),
                env=env,
                cwd=str(self.config.cwd or self.cwd),
                log_file=Path(os.devnull),
            )
        elif self.config.url:
            return SSETransport(url=self.config.url)
        else:
            raise ValueError("MCP server must have either command or url")

    async def connect(self) -> None:
        """
        Connect to the MCP server and discover available tools.

        Raises
        ------
        Exception
            If connection fails.

        Examples
        --------
        >>> await client.connect()
        >>> print(f"Connected: {client.status == MCPServerStatus.CONNECTED}")
        """
        if self.status == MCPServerStatus.CONNECTED:
            return

        self.status = MCPServerStatus.CONNECTING

        try:
            self._client = Client(transport=self._create_transport())

            await self._client.__aenter__()

            tool_result = await self._client.list_tools()
            for tool in tool_result:
                self._tools[tool.name] = MCPToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=(
                        tool.inputSchema if hasattr(tool, "inputSchema") else {}
                    ),
                    server_name=self.name,
                )

            self.status = MCPServerStatus.CONNECTED
            logger.info(
                f"MCP server '{self.name}' connected with {len(self._tools)} tools",
            )
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            logger.error(f"Failed to connect to MCP server '{self.name}': {e}")
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from the MCP server.

        Examples
        --------
        >>> await client.disconnect()
        """
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

        self._tools.clear()
        self.status = MCPServerStatus.DISCONNECTED
        logger.debug(f"MCP server '{self.name}' disconnected")

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on the MCP server.

        Parameters
        ----------
        tool_name : str
            Name of the tool to call.
        arguments : dict[str, Any]
            Arguments for the tool.

        Returns
        -------
        dict[str, Any]
            Result dictionary with 'output' and 'is_error' keys.

        Raises
        ------
        RuntimeError
            If not connected to the server.

        Examples
        --------
        >>> result = await client.call_tool("read_file", {"path": "test.txt"})
        >>> if not result["is_error"]:
        ...     print(result["output"])
        """
        if not self._client or self.status != MCPServerStatus.CONNECTED:
            raise RuntimeError(f"Not connected to server {self.name}")

        result = await self._client.call_tool(tool_name, arguments)

        output: list[str] = []
        for item in result.content:
            if hasattr(item, "text"):
                output.append(item.text)
            else:
                output.append(str(item))

        return {
            "output": "\n".join(output),
            "is_error": result.is_error,
        }
