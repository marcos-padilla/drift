"""
Data models for context management.

This module defines models for representing messages and context items
in conversation management.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    """
    Represents a single message in a conversation context.

    Parameters
    ----------
    role : str
        Message role (user, assistant, tool, system).
    content : str
        Message content.
    tool_call_id : str | None, optional
        Tool call ID if this is a tool result message.
    tool_calls : list[dict[str, Any]], default=[]
        List of tool calls if this is an assistant message with tool calls.
    token_count : int | None, optional
        Cached token count for this message.
    pruned_at : datetime | None, optional
        Timestamp when this message was pruned (if applicable).

    Examples
    --------
    >>> message = MessageItem(
    ...     role="user",
    ...     content="Hello!",
    ...     token_count=5
    ... )
    >>> message_dict = message.to_dict()
    """

    role: str = Field(description="Message role")
    content: str = Field(default="", description="Message content")
    tool_call_id: str | None = Field(default=None, description="Tool call ID")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tool calls in this message",
    )
    token_count: int | None = Field(default=None, description="Cached token count")
    pruned_at: datetime | None = Field(
        default=None,
        description="Timestamp when message was pruned",
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert message to dictionary format for API calls.

        Returns
        -------
        dict[str, Any]
            Message in dictionary format compatible with LLM APIs.

        Examples
        --------
        >>> message = MessageItem(role="user", content="Hello")
        >>> message_dict = message.to_dict()
        >>> # Returns: {"role": "user", "content": "Hello"}
        """
        result: dict[str, Any] = {"role": self.role}

        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        if self.tool_calls:
            result["tool_calls"] = self.tool_calls

        if self.content:
            result["content"] = self.content

        return result
