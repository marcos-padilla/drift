"""
Factory functions for creating and registering tools.

This module provides utility functions for programmatically creating
tool instances and registering them with a registry.
"""

import logging
from typing import Any

from core.config.schema import Configuration
from core.tools.base import Tool
from core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_tool_instance(
    tool_class: type[Tool],
    config: Configuration,
) -> Tool:
    """
    Create a tool instance from a tool class.

    Parameters
    ----------
    tool_class : type[Tool]
        Tool class to instantiate.
    config : Configuration
        Configuration object.

    Returns
    -------
    Tool
        Tool instance.

    Examples
    --------
    >>> tool = create_tool_instance(MyTool, config)
    """
    return tool_class(config)


def register_tool_instance(
    registry: ToolRegistry,
    tool: Tool,
) -> None:
    """
    Register a tool instance with a registry.

    Parameters
    ----------
    registry : ToolRegistry
        Registry to register with.
    tool : Tool
        Tool instance to register.

    Examples
    --------
    >>> tool = MyTool(config)
    >>> register_tool_instance(registry, tool)
    """
    registry.register(tool)
    logger.debug(f"Registered tool instance: {tool.name}")


def create_and_register_tool(
    registry: ToolRegistry,
    tool_class: type[Tool],
    config: Configuration,
) -> Tool:
    """
    Create a tool instance and register it with a registry.

    Parameters
    ----------
    registry : ToolRegistry
        Registry to register with.
    tool_class : type[Tool]
        Tool class to instantiate.
    config : Configuration
        Configuration object.

    Returns
    -------
    Tool
        Created and registered tool instance.

    Examples
    --------
    >>> tool = create_and_register_tool(registry, MyTool, config)
    """
    tool = create_tool_instance(tool_class, config)
    register_tool_instance(registry, tool)
    return tool


def register_tools_from_classes(
    registry: ToolRegistry,
    tool_classes: list[type[Tool]],
    config: Configuration,
) -> list[Tool]:
    """
    Create and register multiple tools from classes.

    Parameters
    ----------
    registry : ToolRegistry
        Registry to register with.
    tool_classes : list[type[Tool]]
        List of tool classes to create and register.
    config : Configuration
        Configuration object.

    Returns
    -------
    list[Tool]
        List of created tool instances.

    Examples
    --------
    >>> tools = register_tools_from_classes(
    ...     registry,
    ...     [MyTool, AnotherTool],
    ...     config
    ... )
    """
    tools: list[Tool] = []
    for tool_class in tool_classes:
        tool = create_and_register_tool(registry, tool_class, config)
        tools.append(tool)
    return tools
