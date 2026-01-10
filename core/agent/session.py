"""
Session management for agent execution.

This module provides session management functionality including
initialization, tool registry setup, context management, and
session statistics.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from core.config.loader import get_data_dir
from core.config.schema import Configuration
from core.context.compaction import ChatCompactor
from core.context.loop_detector import LoopDetector
from core.context.manager import ContextManager
from core.hooks.system import HookSystem
from core.llm.client import LLMClient
from core.safety.approval import ApprovalManager
from core.tools.discovery import ToolDiscoveryManager
from core.tools.mcp.manager import MCPManager
from core.tools.registry import ToolRegistry
from core.tools.builtin import get_all_builtin_tools
from core.tools.subagents.definitions import get_default_subagent_definitions
from core.tools.subagents.tool import SubagentTool

logger = logging.getLogger(__name__)


def create_default_registry(config: Configuration) -> ToolRegistry:
    """
    Create a tool registry with all default tools.

    Parameters
    ----------
    config : Configuration
        Configuration object.

    Returns
    -------
    ToolRegistry
        Registry with all builtin and subagent tools registered.

    Examples
    --------
    >>> registry = create_default_registry(config)
    """
    from core.tools.registry import ToolRegistry

    registry = ToolRegistry(config)

    for tool_class in get_all_builtin_tools():
        registry.register(tool_class(config))

    for subagent_def in get_default_subagent_definitions():
        registry.register(SubagentTool(config, subagent_def))

    return registry


class Session:
    """
    Manages an agent execution session.

    This class coordinates all components needed for agent execution
    including the LLM client, tool registry, context manager, hooks,
    and approval system.

    Parameters
    ----------
    config : Configuration
        Configuration object.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    client : LLMClient
        LLM client instance.
    tool_registry : ToolRegistry
        Tool registry with all available tools.
    context_manager : ContextManager | None
        Context manager (initialized in initialize()).
    discovery_manager : ToolDiscoveryManager
        Tool discovery manager.
    mcp_manager : MCPManager
        MCP server manager.
    chat_compactor : ChatCompactor
        Chat history compactor.
    approval_manager : ApprovalManager
        Approval manager for safety checks.
    loop_detector : LoopDetector
        Loop detection system.
    hook_system : HookSystem
        Hook execution system.
    session_id : str
        Unique session identifier.
    created_at : datetime
        Session creation timestamp.
    updated_at : datetime
        Last update timestamp.
    turn_count : int
        Number of conversation turns.

    Examples
    --------
    >>> session = Session(config)
    >>> await session.initialize()
    >>> stats = session.get_stats()
    """

    def __init__(self, config: Configuration) -> None:
        self.config: Configuration = config
        self.client: LLMClient = LLMClient(config=config)
        self.tool_registry: ToolRegistry = create_default_registry(config)
        self.context_manager: ContextManager | None = None
        self.discovery_manager: ToolDiscoveryManager = ToolDiscoveryManager(
            self.config,
            self.tool_registry,
        )
        self.mcp_manager: MCPManager = MCPManager(self.config)
        self.chat_compactor: ChatCompactor = ChatCompactor(self.client)
        self.approval_manager: ApprovalManager = ApprovalManager(
            config=self.config,
        )
        self.loop_detector: LoopDetector = LoopDetector()
        self.hook_system: HookSystem = HookSystem(config)
        self.session_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

        self.turn_count: int = 0

    async def initialize(self) -> None:
        """
        Initialize the session.

        This method initializes MCP servers, discovers custom tools,
        and sets up the context manager.

        Examples
        --------
        >>> await session.initialize()
        """
        await self.mcp_manager.initialize()
        self.mcp_manager.register_tools(self.tool_registry)

        self.discovery_manager.discover_all()
        self.context_manager = ContextManager(
            config=self.config,
            user_memory=self._load_memory(),
            tools=self.tool_registry.get_schemas(),
        )
        logger.info(f"Session {self.session_id} initialized")

    def _load_memory(self) -> str | None:
        """
        Load user memory from persistent storage.

        Returns
        -------
        str | None
            Formatted memory string if found, None otherwise.
        """
        data_dir: Path = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path: Path = data_dir / "user_memory.json"

        if not path.exists():
            return None

        try:
            content: str = path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(content)
            entries = data.get("entries")
            if not entries:
                return None

            lines: list[str] = ["User preferences and notes:"]
            for key, value in entries.items():
                lines.append(f"- {key}: {value}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Failed to load user memory: {e}")
            return None

    def increment_turn(self) -> int:
        """
        Increment the turn counter.

        Returns
        -------
        int
            New turn count.

        Examples
        --------
        >>> turn = session.increment_turn()
        """
        self.turn_count += 1
        self.updated_at = datetime.now()

        return self.turn_count

    def get_stats(self) -> dict[str, Any]:
        """
        Get session statistics.

        Returns
        -------
        dict[str, Any]
            Dictionary with session statistics.

        Examples
        --------
        >>> stats = session.get_stats()
        >>> print(f"Turns: {stats['turn_count']}")
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "message_count": (
                self.context_manager.message_count
                if self.context_manager
                else 0
            ),
            "token_usage": (
                self.context_manager.total_usage.model_dump()
                if self.context_manager
                else {}
            ),
            "tools_count": len(self.tool_registry.get_tools()),
            "mcp_servers": len(self.tool_registry.connected_mcp_servers),
        }
