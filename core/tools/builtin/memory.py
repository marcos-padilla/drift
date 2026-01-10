"""
Memory tool for persistent storage of user preferences.

This module provides a tool for storing and retrieving persistent
memory across sessions with support for key-value storage.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.config.loader import get_data_dir
from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


class MemoryParams(BaseModel):
    """
    Parameters for the memory tool.

    Parameters
    ----------
    action : str
        Action: 'set', 'get', 'delete', 'list', 'clear'
    key : str | None, optional
        Memory key (required for `set`, `get`, `delete`).
    value : str | None, optional
        Value to store (required for `set`).

    Examples
    --------
    >>> params = MemoryParams(action="set", key="preferred_language", value="Python")
    """

    action: str = Field(
        ...,
        description="Action: 'set', 'get', 'delete', 'list', 'clear'",
    )
    key: str | None = Field(
        None,
        description="Memory key (required for `set`, `get`, `delete`)",
    )
    value: str | None = Field(None, description="Value to store (required for `set`)")


class MemoryTool(Tool):
    """
    Tool for storing and retrieving persistent memory.

    This tool provides key-value storage that persists across sessions,
    useful for remembering user preferences and important context.

    Attributes
    ----------
    name : str
        Tool name: "memory"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: MEMORY
    schema : type[MemoryParams]
        Parameter schema
    """

    name: str = "memory"
    description: str = (
        "Store and retrieve persistent memory. "
        "Use this to remember user preferences, important context or notes."
    )
    kind: ToolKind = ToolKind.MEMORY
    schema: type[MemoryParams] = MemoryParams

    def _load_memory(self) -> dict[str, Any]:
        """
        Load memory from persistent storage.

        Returns
        -------
        dict[str, Any]
            Memory dictionary with entries.
        """
        data_dir: Path = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path: Path = data_dir / "user_memory.json"

        if not path.exists():
            return {"entries": {}}

        try:
            content: str = path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to load memory from {path}: {e}")
            return {"entries": {}}

    def _save_memory(self, memory: dict[str, Any]) -> None:
        """
        Save memory to persistent storage.

        Parameters
        ----------
        memory : dict[str, Any]
            Memory dictionary to save.
        """
        data_dir: Path = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path: Path = data_dir / "user_memory.json"

        path.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the memory tool.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters.

        Returns
        -------
        ToolResult
            Result containing memory operation result.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = MemoryParams(**invocation.params)

        if params.action.lower() == "set":
            if not params.key or not params.value:
                return ToolResult.error_result(
                    "`key` and `value` are required for 'set' action",
                )
            memory = self._load_memory()
            memory["entries"][params.key] = params.value
            self._save_memory(memory)

            return ToolResult.success_result(f"Set memory: {params.key}")
        elif params.action.lower() == "get":
            if not params.key:
                return ToolResult.error_result("`key` required for 'get' action")

            memory = self._load_memory()
            if params.key not in memory.get("entries", {}):
                return ToolResult.success_result(
                    f"Memory not found: {params.key}",
                    metadata={
                        "found": False,
                    },
                )
            return ToolResult.success_result(
                f"Memory found: {params.key}: {memory['entries'][params.key]}",
                metadata={
                    "found": True,
                },
            )
        elif params.action == "delete":
            if not params.key:
                return ToolResult.error_result("`key` required for 'delete' action")
            memory = self._load_memory()
            if params.key not in memory.get("entries", {}):
                return ToolResult.success_result(f"Memory not found: {params.key}")

            del memory["entries"][params.key]
            self._save_memory(memory)

            return ToolResult.success_result(f"Deleted memory: {params.key}")
        elif params.action == "list":
            memory = self._load_memory()
            entries = memory.get("entries", {})
            if not entries:
                return ToolResult.success_result(
                    "No memories stored",
                    metadata={
                        "found": False,
                    },
                )
            lines: list[str] = ["Stored memories:"]
            for key, value in sorted(entries.items()):
                lines.append(f"  {key}: {value}")

            return ToolResult.success_result(
                "\n".join(lines),
                metadata={
                    "found": True,
                },
            )
        elif params.action == "clear":
            memory = self._load_memory()
            count: int = len(memory.get("entries", {}))
            memory["entries"] = {}
            self._save_memory(memory)
            return ToolResult.success_result(f"Cleared {count} memory entries")
        else:
            return ToolResult.error_result(f"Unknown action: {params.action}")
