"""
Decorator-based tool registration.

This module provides decorators for automatically registering tools
with custom names, descriptions, and metadata.
"""

import functools
import logging
from typing import Any, Callable, TypeVar

from core.tools.base import Tool

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=type[Tool])

# Global registry for decorator-registered tools
_registered_tools: dict[str, type[Tool]] = {}


def register_tool(
    name: str | None = None,
    description: str | None = None,
    auto_register: bool = True,
) -> Callable[[T], T]:
    """
    Decorator to register a tool class.

    This decorator can be used to mark tool classes for automatic
    registration and optionally override the tool name and description.

    Parameters
    ----------
    name : str | None, optional
        Custom name for the tool. If None, uses class name.
    description : str | None, optional
        Custom description. If None, uses class docstring or default.
    auto_register : bool, default=True
        Whether to automatically register in global registry.

    Returns
    -------
    Callable[[T], T]
        Decorator function.

    Examples
    --------
    >>> @register_tool(name="custom_tool", description="My custom tool")
    ... class CustomTool(Tool):
    ...     name = "custom_tool"
    ...     description = "My custom tool"
    ...     # ... implementation
    """
    def decorator(cls: T) -> T:
        tool_name = name or getattr(cls, "name", cls.__name__.lower())
        tool_description = description or getattr(
            cls,
            "description",
            cls.__doc__ or "No description",
        )

        # Override if provided
        if name:
            cls.name = tool_name
        if description:
            cls.description = tool_description

        if auto_register:
            _registered_tools[tool_name] = cls
            logger.debug(f"Registered tool via decorator: {tool_name}")

        return cls

    return decorator


def get_registered_tools() -> dict[str, type[Tool]]:
    """
    Get all tools registered via decorator.

    Returns
    -------
    dict[str, type[Tool]]
        Dictionary of tool classes keyed by name.

    Examples
    --------
    >>> tools = get_registered_tools()
    >>> for name, tool_class in tools.items():
    ...     print(f"{name}: {tool_class}")
    """
    return _registered_tools.copy()


def clear_registered_tools() -> None:
    """
    Clear all decorator-registered tools.

    Useful for testing or resetting the registry.

    Examples
    --------
    >>> clear_registered_tools()
    """
    _registered_tools.clear()
    logger.debug("Cleared registered tools")
