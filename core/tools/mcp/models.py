"""
Data models for MCP integration.

This module defines models for MCP server status and tool information.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MCPServerStatus(str, Enum):
    """
    Status of an MCP server connection.

    Attributes
    ----------
    DISCONNECTED : str
        Server is not connected.
    CONNECTING : str
        Connection is in progress.
    CONNECTED : str
        Server is connected and ready.
    ERROR : str
        Connection error occurred.

    Examples
    --------
    >>> status = MCPServerStatus.CONNECTED
    >>> if status == MCPServerStatus.CONNECTED:
    ...     # Server is ready
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPToolInfo(BaseModel):
    """
    Information about an MCP tool.

    Parameters
    ----------
    name : str
        Name of the tool.
    description : str
        Description of what the tool does.
    input_schema : dict[str, Any], default={}
        JSON schema for tool input parameters.
    server_name : str, default=""
        Name of the MCP server providing this tool.

    Examples
    --------
    >>> tool_info = MCPToolInfo(
    ...     name="read_file",
    ...     description="Read a file",
    ...     server_name="filesystem"
    ... )
    """

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameter schema",
    )
    server_name: str = Field(default="", description="MCP server name")
