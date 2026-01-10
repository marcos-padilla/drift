"""
Test script for tool execution.

This script provides a simple way to test tool execution outside
of the main agent loop.
"""

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.config.loader import load_configuration
from core.tools.registry import ToolRegistry
from core.tools.builtin import get_all_builtin_tools
from core.hooks.system import HookSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tool_execution() -> None:
    """
    Test tool execution with a simple example.

    This function demonstrates how to create a tool registry,
    register tools, and execute them.

    Examples
    --------
    >>> asyncio.run(test_tool_execution())
    """
    load_dotenv()

    # Load configuration
    config = load_configuration()
    logger.info("Configuration loaded")

    # Create tool registry
    registry = ToolRegistry(config)

    # Register builtin tools
    for tool_class in get_all_builtin_tools():
        tool = tool_class(config)
        registry.register(tool)
        logger.info(f"Registered tool: {tool.name}")

    # Create hook system
    hook_system = HookSystem(config)

    # Test read_file tool
    logger.info("Testing read_file tool...")
    result = await registry.invoke(
        "read_file",
        {"path": "main.py"},
        Path.cwd(),
        hook_system,
    )

    if result.success:
        logger.info(f"Tool executed successfully:\n{result.output[:200]}")
    else:
        logger.error(f"Tool execution failed: {result.error}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    asyncio.run(test_tool_execution())
