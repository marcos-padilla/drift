"""
Tool discovery system for finding and loading tools from directories.

This module provides functionality to discover and load custom tools
from project directories and configuration directories.
"""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Any

from core.config.loader import get_config_dir
from core.config.schema import Configuration
from core.tools.base import Tool
from core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolDiscoveryManager:
    """
    Manages discovery and loading of tools from directories.

    This class searches for tool classes in specified directories
    and automatically registers them with the tool registry.

    Parameters
    ----------
    config : Configuration
        Configuration object.
    registry : ToolRegistry
        Tool registry to register discovered tools with.

    Examples
    --------
    >>> manager = ToolDiscoveryManager(config, registry)
    >>> manager.discover_all()
    """

    def __init__(
        self,
        config: Configuration,
        registry: ToolRegistry,
    ) -> None:
        self.config: Configuration = config
        self.registry: ToolRegistry = registry

    def _load_tool_modules(self, file_path: Path) -> Any:
        """
        Load a Python module from a file path.

        Parameters
        ----------
        file_path : Path
            Path to the Python file to load.

        Returns
        -------
        Any
            Loaded module object.

        Raises
        ------
        ImportError
            If the module cannot be loaded.
        """
        module_name: str = f"discovered_tool_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)

        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        spec.loader.exec_module(module)
        return module

    def _find_tool_classes(self, module: Any) -> list[type[Tool]]:
        """
        Find all Tool subclasses in a module.

        Parameters
        ----------
        module : Any
            Module to search for tool classes.

        Returns
        -------
        list[type[Tool]]
            List of tool classes found in the module.
        """
        tools: list[type[Tool]] = []

        for name in dir(module):
            obj = getattr(module, name)
            if (
                inspect.isclass(obj)
                and issubclass(obj, Tool)
                and obj is not Tool
                and obj.__module__ == module.__name__
            ):
                tools.append(obj)

        return tools

    def discover_from_directory(self, directory: Path) -> None:
        """
        Discover tools from a directory.

        Searches for `.ai-agent/tools/*.py` files in the given directory
        and loads any Tool classes found.

        Parameters
        ----------
        directory : Path
            Directory to search for tools.

        Examples
        --------
        >>> manager.discover_from_directory(Path("/path/to/project"))
        """
        tool_dir: Path = directory / ".ai-agent" / "tools"

        if not tool_dir.exists() or not tool_dir.is_dir():
            return

        for py_file in tool_dir.glob("*.py"):
            try:
                if py_file.name.startswith("__"):
                    continue

                module = self._load_tool_modules(py_file)
                tool_classes = self._find_tool_classes(module)

                if not tool_classes:
                    continue

                for tool_class in tool_classes:
                    tool = tool_class(self.config)
                    self.registry.register(tool)
                    logger.info(f"Discovered and registered tool: {tool.name}")

            except Exception as e:
                logger.warning(
                    f"Failed to load tool from {py_file}: {e}",
                    exc_info=True,
                )

    def discover_all(self) -> None:
        """
        Discover tools from all configured directories.

        Searches the current working directory and the user config directory
        for custom tools.

        Examples
        --------
        >>> manager.discover_all()
        """
        self.discover_from_directory(self.config.cwd)
        self.discover_from_directory(get_config_dir())
