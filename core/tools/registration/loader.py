"""
Tool loading utilities for discovering and loading tools.

This module provides functions for loading tools from modules,
directories, and packages with automatic discovery.
"""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any

from core.config.schema import Configuration
from core.tools.base import Tool
from core.tools.registration.decorator import get_registered_tools
from core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def load_tools_from_module(
    module: Any,
    config: Configuration,
) -> list[Tool]:
    """
    Load all Tool classes from a module.

    Parameters
    ----------
    module : Any
        Python module to search for tools.
    config : Configuration
        Configuration object for tool instantiation.

    Returns
    -------
    list[Tool]
        List of tool instances found in the module.

    Examples
    --------
    >>> import my_tools_module
    >>> tools = load_tools_from_module(my_tools_module, config)
    """
    tools: list[Tool] = []

    for name in dir(module):
        obj = getattr(module, name)
        if (
            inspect.isclass(obj)
            and issubclass(obj, Tool)
            and obj is not Tool
            and obj.__module__ == module.__name__
        ):
            try:
                tool = obj(config)
                tools.append(tool)
                logger.debug(f"Loaded tool from module: {tool.name}")
            except Exception as e:
                logger.warning(
                    f"Failed to instantiate tool {name} from {module.__name__}: {e}",
                )

    return tools


def load_tools_from_package(
    package: Any,
    config: Configuration,
) -> list[Tool]:
    """
    Load all Tool classes from a package and its submodules.

    Parameters
    ----------
    package : Any
        Python package to search for tools.
    config : Configuration
        Configuration object for tool instantiation.

    Returns
    -------
    list[Tool]
        List of tool instances found in the package.

    Examples
    --------
    >>> import my_tools_package
    >>> tools = load_tools_from_package(my_tools_package, config)
    """
    tools: list[Tool] = []

    # Load from main package
    if hasattr(package, "__path__"):
        tools.extend(load_tools_from_module(package, config))

        # Load from submodules
        for importer, modname, ispkg in pkgutil.walk_packages(
            package.__path__,
            package.__name__ + ".",
        ):
            try:
                module = importlib.import_module(modname)
                tools.extend(load_tools_from_module(module, config))
            except Exception as e:
                logger.warning(f"Failed to load module {modname}: {e}")

    return tools


def load_decorator_registered_tools(
    config: Configuration,
) -> list[Tool]:
    """
    Load all tools registered via the @register_tool decorator.

    Parameters
    ----------
    config : Configuration
        Configuration object for tool instantiation.

    Returns
    -------
    list[Tool]
        List of tool instances from decorator registration.

    Examples
    --------
    >>> tools = load_decorator_registered_tools(config)
    """
    tools: list[Tool] = []
    registered = get_registered_tools()

    for tool_class in registered.values():
        try:
            tool = tool_class(config)
            tools.append(tool)
            logger.debug(f"Loaded decorator-registered tool: {tool.name}")
        except Exception as e:
            logger.warning(f"Failed to instantiate decorator tool: {e}")

    return tools


def auto_discover_tools(
    registry: ToolRegistry,
    config: Configuration,
    *,
    include_decorator_tools: bool = True,
    include_builtin: bool = True,
) -> None:
    """
    Automatically discover and register tools from various sources.

    Parameters
    ----------
    registry : ToolRegistry
        Registry to register tools with.
    config : Configuration
        Configuration object.
    include_decorator_tools : bool, default=True
        Whether to include decorator-registered tools.
    include_builtin : bool, default=True
        Whether to include builtin tools (if available).

    Examples
    --------
    >>> auto_discover_tools(registry, config)
    """
    if include_decorator_tools:
        decorator_tools = load_decorator_registered_tools(config)
        for tool in decorator_tools:
            registry.register(tool)

    # Builtin tools are typically registered separately
    # This is a placeholder for future auto-discovery of builtin tools
    if include_builtin:
        logger.debug("Builtin tools should be registered separately")
