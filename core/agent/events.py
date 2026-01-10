"""
Event models for agent lifecycle and operations.

This module defines event types and models for tracking agent operations,
tool calls, and text streaming.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from core.llm.models import TokenUsage
from core.tools.models import ToolResult


class AgentEventType(str, Enum):
    """
    Types of events emitted by the agent.

    Attributes
    ----------
    AGENT_START : str
        Agent started processing a message.
    AGENT_END : str
        Agent finished processing.
    AGENT_ERROR : str
        Agent encountered an error.
    TOOL_CALL_START : str
        Tool call started.
    TOOL_CALL_COMPLETE : str
        Tool call completed.
    TEXT_DELTA : str
        Text delta in streaming response.
    TEXT_COMPLETE : str
        Complete text response received.

    Examples
    --------
    >>> event_type = AgentEventType.AGENT_START
    >>> if event_type == AgentEventType.TEXT_DELTA:
    ...     # Handle text streaming
    """

    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"

    # Tool calls
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"

    # Text streaming
    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"


class AgentEvent(BaseModel):
    """
    Event emitted by the agent during execution.

    Parameters
    ----------
    type : AgentEventType
        Type of the event.
    data : dict[str, Any], default={}
        Event-specific data.

    Examples
    --------
    >>> event = AgentEvent.agent_start("Hello")
    >>> event = AgentEvent.text_delta("Hello")
    >>> event = AgentEvent.tool_call_complete("call_123", "read_file", result)
    """

    type: AgentEventType = Field(description="Event type")
    data: dict[str, Any] = Field(default_factory=dict, description="Event data")

    @classmethod
    def agent_start(cls, message: str) -> "AgentEvent":
        """
        Create an agent start event.

        Parameters
        ----------
        message : str
            User message that started the agent.

        Returns
        -------
        AgentEvent
            Agent start event.
        """
        return cls(
            type=AgentEventType.AGENT_START,
            data={"message": message},
        )

    @classmethod
    def agent_end(
        cls,
        response: str | None = None,
        usage: TokenUsage | None = None,
    ) -> "AgentEvent":
        """
        Create an agent end event.

        Parameters
        ----------
        response : str | None, optional
            Final response text.
        usage : TokenUsage | None, optional
            Token usage statistics.

        Returns
        -------
        AgentEvent
            Agent end event.
        """
        return cls(
            type=AgentEventType.AGENT_END,
            data={
                "response": response,
                "usage": usage.model_dump() if usage else None,
            },
        )

    @classmethod
    def agent_error(
        cls,
        error: str,
        details: dict[str, Any] | None = None,
    ) -> "AgentEvent":
        """
        Create an agent error event.

        Parameters
        ----------
        error : str
            Error message.
        details : dict[str, Any] | None, optional
            Additional error details.

        Returns
        -------
        AgentEvent
            Agent error event.
        """
        return cls(
            type=AgentEventType.AGENT_ERROR,
            data={"error": error, "details": details or {}},
        )

    @classmethod
    def text_delta(cls, content: str) -> "AgentEvent":
        """
        Create a text delta event.

        Parameters
        ----------
        content : str
            Text content delta.

        Returns
        -------
        AgentEvent
            Text delta event.
        """
        return cls(
            type=AgentEventType.TEXT_DELTA,
            data={"content": content},
        )

    @classmethod
    def text_complete(cls, content: str) -> "AgentEvent":
        """
        Create a text complete event.

        Parameters
        ----------
        content : str
            Complete text content.

        Returns
        -------
        AgentEvent
            Text complete event.
        """
        return cls(
            type=AgentEventType.TEXT_COMPLETE,
            data={"content": content},
        )

    @classmethod
    def tool_call_start(
        cls,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
    ) -> "AgentEvent":
        """
        Create a tool call start event.

        Parameters
        ----------
        call_id : str
            Tool call ID.
        name : str
            Tool name.
        arguments : dict[str, Any]
            Tool arguments.

        Returns
        -------
        AgentEvent
            Tool call start event.
        """
        return cls(
            type=AgentEventType.TOOL_CALL_START,
            data={
                "call_id": call_id,
                "name": name,
                "arguments": arguments,
            },
        )

    @classmethod
    def tool_call_complete(
        cls,
        call_id: str,
        name: str,
        result: ToolResult,
    ) -> "AgentEvent":
        """
        Create a tool call complete event.

        Parameters
        ----------
        call_id : str
            Tool call ID.
        name : str
            Tool name.
        result : ToolResult
            Tool execution result.

        Returns
        -------
        AgentEvent
            Tool call complete event.
        """
        return cls(
            type=AgentEventType.TOOL_CALL_COMPLETE,
            data={
                "call_id": call_id,
                "name": name,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "metadata": result.metadata,
                "diff": result.diff.to_diff() if result.diff else None,
                "truncated": result.truncated,
                "exit_code": result.exit_code,
            },
        )
