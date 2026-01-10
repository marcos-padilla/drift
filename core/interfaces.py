"""
Protocol definitions for extensible interfaces in the Drift framework.

This module defines protocols (interfaces) that allow for flexible
implementation and testing through dependency injection.
"""

from typing import Any, AsyncGenerator, Protocol
from pathlib import Path

from core.llm.models import StreamEvent
from core.types import MessageDict, ToolDefinitions


class LLMClientProtocol(Protocol):
    """
    Protocol for LLM client implementations.

    This protocol defines the interface that all LLM clients must implement,
    allowing for different providers or implementations to be used interchangeably.
    """

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
            Events from the streaming response.

        Raises
        ------
        Exception
            Various exceptions may be raised depending on the implementation.
        """
        ...

    async def close(self) -> None:
        """
        Close the client and release any resources.

        This method should be called when the client is no longer needed
        to ensure proper cleanup of connections and resources.
        """
        ...


class ConfigLoaderProtocol(Protocol):
    """
    Protocol for configuration loader implementations.

    This protocol defines the interface for loading and merging configuration
    from various sources (files, environment, etc.).
    """

    def load(self, cwd: Path | None = None) -> Any:
        """
        Load configuration from the appropriate sources.

        Parameters
        ----------
        cwd : Path | None, optional
            Current working directory to use for resolving relative paths.
            If None, uses the current working directory.

        Returns
        -------
        Any
            The loaded configuration object.

        Raises
        ------
        Exception
            Various exceptions may be raised if configuration loading fails.
        """
        ...


class TokenizerProtocol(Protocol):
    """
    Protocol for tokenizer implementations.

    This protocol defines the interface for token counting and text processing
    operations.
    """

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.

        Parameters
        ----------
        text : str
            The text to count tokens for.

        Returns
        -------
        int
            The number of tokens in the text.
        """
        ...

    def truncate(
        self,
        text: str,
        max_tokens: int,
        suffix: str = "\n... [truncated]",
        preserve_lines: bool = True,
    ) -> str:
        """
        Truncate text to fit within a token limit.

        Parameters
        ----------
        text : str
            The text to truncate.
        max_tokens : int
            Maximum number of tokens allowed.
        suffix : str, default="\\n... [truncated]"
            Suffix to append when text is truncated.
        preserve_lines : bool, default=True
            Whether to preserve complete lines when truncating.

        Returns
        -------
        str
            The truncated text.
        """
        ...
