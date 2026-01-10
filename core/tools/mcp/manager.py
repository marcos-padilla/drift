"""
MCP manager for managing multiple MCP server connections.

This module provides functionality to initialize, manage, and shutdown
multiple MCP server connections and register their tools.
"""

import asyncio
import logging
from typing import Any

from core.config.schema import Configuration
from core.tools.mcp.client import MCPClient, MCPServerStatus
from core.tools.mcp.tool import MCPTool
from core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manages multiple MCP server connections.

    This class handles initialization, connection management, and tool
    registration for all configured MCP servers.

    Parameters
    ----------
    config : Configuration
        Configuration object with MCP server settings.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    _clients : dict[str, MCPClient]
        Dictionary of MCP clients keyed by server name.
    _initialized : bool
        Whether the manager has been initialized.

    Examples
    --------
    >>> manager = MCPManager(config)
    >>> await manager.initialize()
    >>> count = manager.register_tools(registry)
    >>> await manager.shutdown()
    """

    def __init__(self, config: Configuration) -> None:
        self.config: Configuration = config
        self._clients: dict[str, MCPClient] = {}
        self._initialized: bool = False

    async def initialize(self) -> None:
        """
        Initialize and connect to all configured MCP servers.

        This method creates clients for all enabled MCP servers and
        attempts to connect to them in parallel.

        Examples
        --------
        >>> await manager.initialize()
        """
        if self._initialized:
            return

        mcp_configs = self.config.mcp_servers

        if not mcp_configs:
            logger.debug("No MCP servers configured")
            self._initialized = True
            return

        for name, server_config in mcp_configs.items():
            if not server_config.enabled:
                logger.debug(f"MCP server '{name}' is disabled, skipping")
                continue

            self._clients[name] = MCPClient(
                name=name,
                config=server_config,
                cwd=self.config.cwd,
            )

        connection_tasks = [
            asyncio.wait_for(
                client.connect(),
                timeout=client.config.startup_timeout_sec,
            )
            for name, client in self._clients.items()
        ]

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        # Log connection results
        for (name, client), result in zip(self._clients.items(), results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Failed to connect to MCP server '{name}': {result}",
                )
            else:
                logger.info(f"MCP server '{name}' connected successfully")

        self._initialized = True

    def register_tools(self, registry: ToolRegistry) -> int:
        """
        Register all tools from connected MCP servers.

        Parameters
        ----------
        registry : ToolRegistry
            Tool registry to register tools with.

        Returns
        -------
        int
            Number of tools registered.

        Examples
        --------
        >>> count = manager.register_tools(registry)
        >>> print(f"Registered {count} MCP tools")
        """
        count: int = 0

        for client in self._clients.values():
            if client.status != MCPServerStatus.CONNECTED:
                continue

            for tool_info in client.tools:
                mcp_tool = MCPTool(
                    config=self.config,
                    client=client,
                    tool_info=tool_info,
                    name=f"{client.name}__{tool_info.name}",
                )
                registry.register_mcp_tool(mcp_tool)
                count += 1

        logger.info(f"Registered {count} MCP tools")
        return count

    async def shutdown(self) -> None:
        """
        Shutdown all MCP server connections.

        Examples
        --------
        >>> await manager.shutdown()
        """
        disconnection_tasks = [
            client.disconnect() for client in self._clients.values()
        ]

        await asyncio.gather(*disconnection_tasks, return_exceptions=True)

        self._clients.clear()
        self._initialized = False
        logger.info("MCP manager shut down")

    def get_all_servers(self) -> list[dict[str, Any]]:
        """
        Get information about all configured MCP servers.

        Returns
        -------
        list[dict[str, Any]]
            List of server information dictionaries.

        Examples
        --------
        >>> servers = manager.get_all_servers()
        >>> for server in servers:
        ...     print(f"{server['name']}: {server['status']}")
        """
        servers: list[dict[str, Any]] = []
        for name, client in self._clients.items():
            server_info: dict[str, Any] = {
                "name": name,
                "status": client.status.value,
                "tools": len(client.tools),
            }
            servers.append(server_info)

        return servers
