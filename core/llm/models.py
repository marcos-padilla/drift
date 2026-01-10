"""
Data models for LLM interactions and responses.

This module defines Pydantic models for representing LLM responses, including
streaming events, token usage, tool calls, and message deltas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class StreamEventType(str, Enum):
    """Types of events in a streaming response."""

    TEXT_DELTA = "text_delta"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_COMPLETE = "tool_call_complete"


class TextDelta(BaseModel):
    """
    Represents a delta (incremental change) in text content.

    Parameters
    ----------
    content : str
        The text content of this delta.

    Examples
    --------
    >>> delta = TextDelta(content="Hello")
    >>> print(delta.content)
    Hello
    """

    content: str = Field(description="Text content")

    def __str__(self) -> str:
        """
        Return the content as a string.

        Returns
        -------
        str
            The text content.
        """
        return self.content


class TokenUsage(BaseModel):
    """
    Represents token usage statistics for an LLM request.

    Parameters
    ----------
    prompt_tokens : int, default=0
        Number of tokens in the prompt.
    completion_tokens : int, default=0
        Number of tokens in the completion.
    total_tokens : int, default=0
        Total number of tokens used.
    cached_tokens : int, default=0
        Number of tokens that were cached.

    Examples
    --------
    >>> usage = TokenUsage(
    ...     prompt_tokens=100,
    ...     completion_tokens=50,
    ...     total_tokens=150
    ... )
    >>> print(usage.total_tokens)
    150
    """

    prompt_tokens: int = Field(default=0, ge=0, description="Prompt tokens")
    completion_tokens: int = Field(default=0, ge=0, description="Completion tokens")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens")
    cached_tokens: int = Field(default=0, ge=0, description="Cached tokens")

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """
        Add two TokenUsage objects together.

        Parameters
        ----------
        other : TokenUsage
            Another TokenUsage object to add.

        Returns
        -------
        TokenUsage
            New TokenUsage with summed values.

        Examples
        --------
        >>> usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50)
        >>> usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100)
        >>> total = usage1 + usage2
        >>> print(total.total_tokens)
        450
        """
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )


class ToolCallDelta(BaseModel):
    """
    Represents a delta in a tool call during streaming.

    Parameters
    ----------
    call_id : str
        Unique identifier for this tool call.
    name : str | None, optional
        Name of the tool being called.
    arguments_delta : str, default=""
        Incremental arguments for the tool call.

    Examples
    --------
    >>> delta = ToolCallDelta(
    ...     call_id="call_123",
    ...     name="search",
    ...     arguments_delta='{"query": "test"}'
    ... )
    """

    call_id: str = Field(description="Tool call identifier")
    name: str | None = Field(default=None, description="Tool name")
    arguments_delta: str = Field(default="", description="Incremental arguments")


class ToolCall(BaseModel):
    """
    Represents a complete tool call.

    Parameters
    ----------
    call_id : str
        Unique identifier for this tool call.
    name : str | None, optional
        Name of the tool being called.
    arguments : dict[str, Any] | str, default=""
        Arguments for the tool call. Can be a dictionary or JSON string.

    Examples
    --------
    >>> call = ToolCall(
    ...     call_id="call_123",
    ...     name="search",
    ...     arguments={"query": "test", "limit": 10}
    ... )
    """

    call_id: str = Field(description="Tool call identifier")
    name: str | None = Field(default=None, description="Tool name")
    arguments: dict[str, Any] | str = Field(
        default="",
        description="Tool call arguments",
    )

    @field_validator("arguments", mode="before")
    @classmethod
    def parse_arguments(cls, v: Any) -> dict[str, Any] | str:
        """
        Parse arguments if they are a JSON string.

        Parameters
        ----------
        v : Any
            Arguments value (dict, str, or other).

        Returns
        -------
        dict[str, Any] | str
            Parsed arguments as dict if valid JSON, otherwise original value.
        """
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


class StreamEvent(BaseModel):
    """
    Represents an event in a streaming LLM response.

    Parameters
    ----------
    type : StreamEventType
        Type of the event.
    text_delta : TextDelta | None, optional
        Text delta if this is a text event.
    error : str | None, optional
        Error message if this is an error event.
    finish_reason : str | None, optional
        Reason for completion if this is a completion event.
    tool_call_delta : ToolCallDelta | None, optional
        Tool call delta if this is a tool call delta event.
    tool_call : ToolCall | None, optional
        Complete tool call if this is a tool call complete event.
    usage : TokenUsage | None, optional
        Token usage statistics if available.

    Examples
    --------
    >>> event = StreamEvent(
    ...     type=StreamEventType.TEXT_DELTA,
    ...     text_delta=TextDelta(content="Hello")
    ... )
    """

    type: StreamEventType = Field(description="Event type")
    text_delta: TextDelta | None = Field(default=None, description="Text delta")
    error: str | None = Field(default=None, description="Error message")
    finish_reason: str | None = Field(default=None, description="Finish reason")
    tool_call_delta: ToolCallDelta | None = Field(
        default=None,
        description="Tool call delta",
    )
    tool_call: ToolCall | None = Field(default=None, description="Complete tool call")
    usage: TokenUsage | None = Field(default=None, description="Token usage")


class ToolResultMessage(BaseModel):
    """
    Represents a result message from a tool execution.

    Parameters
    ----------
    tool_call_id : str
        ID of the tool call this result corresponds to.
    content : str
        Content of the tool result.
    is_error : bool, default=False
        Whether this result represents an error.

    Examples
    --------
    >>> result = ToolResultMessage(
    ...     tool_call_id="call_123",
    ...     content='{"result": "success"}',
    ...     is_error=False
    ... )
    """

    tool_call_id: str = Field(description="Tool call identifier")
    content: str = Field(description="Result content")
    is_error: bool = Field(default=False, description="Whether this is an error")

    def to_openai_message(self) -> dict[str, Any]:
        """
        Convert to OpenAI message format.

        Returns
        -------
        dict[str, Any]
            Message in OpenAI format.

        Examples
        --------
        >>> result = ToolResultMessage(
        ...     tool_call_id="call_123",
        ...     content="Result"
        ... )
        >>> message = result.to_openai_message()
        >>> # Returns: {"role": "tool", "tool_call_id": "call_123", "content": "Result"}
        """
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": self.content,
        }


def parse_tool_call_arguments(arguments_str: str) -> dict[str, Any]:
    """
    Parse tool call arguments from a JSON string.

    Parameters
    ----------
    arguments_str : str
        JSON string containing tool call arguments.

    Returns
    -------
    dict[str, Any]
        Parsed arguments as a dictionary. Returns empty dict if string is empty,
        or a dict with "raw_arguments" key if parsing fails.

    Examples
    --------
    >>> args = parse_tool_call_arguments('{"query": "test", "limit": 10}')
    >>> print(args["query"])
    test
    >>> # Invalid JSON returns raw string
    >>> args = parse_tool_call_arguments("invalid json")
    >>> print(args["raw_arguments"])
    invalid json
    """
    if not arguments_str:
        return {}

    try:
        return json.loads(arguments_str)
    except json.JSONDecodeError:
        return {"raw_arguments": arguments_str}
