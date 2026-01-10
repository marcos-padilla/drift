"""
LLM client implementation for the Drift framework.

This module provides an async client for interacting with LLM APIs,
supporting both streaming and non-streaming responses with proper
error handling and retry logic.
"""

import logging
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from core.config.schema import Configuration
from core.exceptions import APIError, ConnectionError
from core.interfaces import LLMClientProtocol
from core.llm.models import (
    StreamEvent,
    StreamEventType,
    TextDelta,
    TokenUsage,
    ToolCall,
    ToolCallDelta,
    parse_tool_call_arguments,
)
from core.llm.retry import RetryStrategy
from core.types import MessageDict, ToolDefinitions

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with LLM APIs.

    This client provides async methods for generating completions with
    support for streaming, tool calls, and automatic retry logic.

    Parameters
    ----------
    config : Configuration
        Configuration object containing API settings and model parameters.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    _client : AsyncOpenAI | None
        Internal OpenAI client instance (lazy-initialized).
    _retry_strategy : RetryStrategy
        Strategy for handling retries.

    Examples
    --------
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> client = LLMClient(config)
    >>> async for event in client.chat_completion([{"role": "user", "content": "Hello"}]):
    ...     if event.type == StreamEventType.TEXT_DELTA:
    ...         print(event.text_delta.content, end="")
    >>> await client.close()
    """

    def __init__(self, config: Configuration) -> None:
        self.config: Configuration = config
        self._client: AsyncOpenAI | None = None
        self._retry_strategy: RetryStrategy = RetryStrategy(max_retries=3)

    def _get_client(self) -> AsyncOpenAI:
        """
        Get or create the OpenAI client instance.

        Returns
        -------
        AsyncOpenAI
            The OpenAI client instance.

        Raises
        ------
        ConnectionError
            If API key is not configured.
        """
        if self._client is None:
            api_key: str | None = self.config.api_key
            if not api_key:
                raise ConnectionError(
                    "API key not configured. Set API_KEY environment variable.",
                )

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self.config.base_url,
            )
            logger.debug("LLM client initialized")

        return self._client

    async def close(self) -> None:
        """
        Close the client and release resources.

        This method should be called when the client is no longer needed
        to ensure proper cleanup of connections.

        Examples
        --------
        >>> client = LLMClient(config)
        >>> # ... use client ...
        >>> await client.close()
        """
        if self._client:
            await self._client.close()
            self._client = None
            logger.debug("LLM client closed")

    def _build_tools(self, tools: ToolDefinitions) -> list[dict[str, Any]]:
        """
        Build tool definitions in OpenAI format.

        Parameters
        ----------
        tools : ToolDefinitions
            List of tool definitions.

        Returns
        -------
        list[dict[str, Any]]
            Tool definitions in OpenAI format.

        Examples
        --------
        >>> tools = [{"name": "search", "description": "Search the web"}]
        >>> formatted = client._build_tools(tools)
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                },
            }
            for tool in tools
        ]

    async def chat_completion(
        self,
        messages: list[MessageDict],
        tools: ToolDefinitions | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Generate a chat completion from the LLM.

        Parameters
        ----------
        messages : list[MessageDict]
            List of messages in the conversation.
        tools : ToolDefinitions | None, optional
            Optional list of tool definitions available to the model.
        stream : bool, default=True
            Whether to stream the response or return it all at once.

        Yields
        ------
        StreamEvent
            Events from the streaming response, including text deltas,
            tool calls, completion events, and errors.

        Raises
        ------
        ConnectionError
            If connection to the API fails.
        APIError
            If the API returns an error.

        Examples
        --------
        >>> messages = [{"role": "user", "content": "Hello!"}]
        >>> async for event in client.chat_completion(messages):
        ...     if event.type == StreamEventType.TEXT_DELTA:
        ...         print(event.text_delta.content, end="")
        """
        client: AsyncOpenAI = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": stream,
            "temperature": self.config.temperature,
        }

        if tools:
            kwargs["tools"] = self._build_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            if stream:
                async for event in self._stream_response(client, kwargs):
                    yield event
            else:
                event: StreamEvent = await self._retry_strategy.execute(
                    lambda: self._non_stream_response(client, kwargs),
                )
                yield event
        except Exception as e:
            logger.error(f"Error in chat completion: {e}", exc_info=True)
            yield StreamEvent(
                type=StreamEventType.ERROR,
                error=str(e),
            )

    async def _stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Handle streaming response from the API.

        Parameters
        ----------
        client : AsyncOpenAI
            The OpenAI client instance.
        kwargs : dict[str, Any]
            Arguments for the chat completion request.

        Yields
        ------
        StreamEvent
            Streaming events from the response.
        """
        response = await self._retry_strategy.execute(
            lambda: client.chat.completions.create(**kwargs),
        )

        finish_reason: str | None = None
        usage: TokenUsage | None = None
        tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens or 0,
                    completion_tokens=chunk.usage.completion_tokens or 0,
                    total_tokens=chunk.usage.total_tokens or 0,
                    cached_tokens=(
                        chunk.usage.prompt_tokens_details.cached_tokens
                        if hasattr(chunk.usage, "prompt_tokens_details")
                        and chunk.usage.prompt_tokens_details
                        else 0
                    ),
                )

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(content=delta.content),
                )

            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx: int = tool_call_delta.index

                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }

                        if tool_call_delta.function and tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_START,
                                tool_call_delta=ToolCallDelta(
                                    call_id=tool_calls[idx]["id"],
                                    name=tool_call_delta.function.name,
                                ),
                            )

                    if tool_call_delta.function and tool_call_delta.function.arguments:
                        tool_calls[idx]["arguments"] += tool_call_delta.function.arguments

                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_DELTA,
                            tool_call_delta=ToolCallDelta(
                                call_id=tool_calls[idx]["id"],
                                name=tool_calls[idx]["name"],
                                arguments_delta=tool_call_delta.function.arguments,
                            ),
                        )

        # Emit complete tool calls
        for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=parse_tool_call_arguments(tc["arguments"]),
                ),
            )

        # Emit completion event
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )

    async def _non_stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> StreamEvent:
        """
        Handle non-streaming response from the API.

        Parameters
        ----------
        client : AsyncOpenAI
            The OpenAI client instance.
        kwargs : dict[str, Any]
            Arguments for the chat completion request.

        Returns
        -------
        StreamEvent
            A single completion event with the full response.
        """
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        text_delta: TextDelta | None = None
        if message.content:
            text_delta = TextDelta(content=message.content)

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=parse_tool_call_arguments(tc.function.arguments),
                    ),
                )

        usage: TokenUsage | None = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens or 0,
                cached_tokens=(
                    response.usage.prompt_tokens_details.cached_tokens
                    if hasattr(response.usage, "prompt_tokens_details")
                    and response.usage.prompt_tokens_details
                    else 0
                ),
            )

        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage,
            tool_call=ToolCall(
                call_id="",
                name=None,
                arguments={},
            ) if tool_calls else None,
        )
