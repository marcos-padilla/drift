"""
Conversation compaction for managing context length.

This module provides functionality to compress conversation history
when it exceeds context limits, preserving important information while
reducing token usage.
"""

import logging
from typing import Any

from core.context.manager import ContextManager
from core.llm.client import LLMClient
from core.llm.models import StreamEventType, TokenUsage
from core.prompts.builder import get_compression_prompt
from core.types import MessageDict

logger = logging.getLogger(__name__)


class ChatCompactor:
    """
    Compacts conversation history to reduce token usage.

    This class provides functionality to compress long conversation
    histories into summaries when context limits are approached.

    Parameters
    ----------
    client : LLMClient
        LLM client to use for generating compression summaries.

    Examples
    --------
    >>> from core.llm.client import LLMClient
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> client = LLMClient(config)
    >>> compactor = ChatCompactor(client)
    >>> summary, usage = await compactor.compress(context_manager)
    """

    def __init__(self, client: LLMClient) -> None:
        self.client: LLMClient = client

    def _format_history_for_compaction(
        self,
        messages: list[MessageDict],
    ) -> str:
        """
        Format conversation history for compression.

        Parameters
        ----------
        messages : list[MessageDict]
            List of messages to format.

        Returns
        -------
        str
            Formatted conversation history as a string.

        Examples
        --------
        >>> formatted = compactor._format_history_for_compaction(messages)
        """
        output: list[str] = ["Here is the conversation that needs to be continued:\n"]

        for msg in messages:
            role: str = msg.get("role", "")
            content: str = msg.get("content", "")

            if role == "system":
                continue

            if role == "tool":
                tool_id: str = msg.get("tool_call_id", "unknown")

                truncated: str = content[:2000] if len(content) > 2000 else content
                if len(content) > 2000:
                    truncated += "\n... [tool output truncated]"

                output.append(f"[Tool Result ({tool_id})]:\n{truncated}")
            elif role == "assistant":
                tool_details: list[str] = []
                if content:
                    truncated = content[:3000] if len(content) > 3000 else content
                    if len(content) > 3000:
                        truncated += "\n... [response truncated]"
                    output.append(f"Assistant:\n{truncated}")

                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        name: str = func.get("name", "unknown")
                        args: str = func.get("arguments", "{}")

                        if len(args) > 500:
                            args = args[:500] + "..."
                        tool_details.append(f"  - {name}({args})")

                    if tool_details:
                        output.append(
                            "Assistant called tools:\n" + "\n".join(tool_details),
                        )
            else:
                truncated = content[:1500] if len(content) > 1500 else content
                if len(content) > 1500:
                    truncated += "\n... [message truncated]"
                output.append(f"User:\n{truncated}")

        return "\n\n---\n\n".join(output)

    async def compress(
        self,
        context_manager: ContextManager,
    ) -> tuple[str | None, TokenUsage | None]:
        """
        Compress conversation history into a summary.

        Parameters
        ----------
        context_manager : ContextManager
            Context manager containing the conversation to compress.

        Returns
        -------
        tuple[str | None, TokenUsage | None]
            Tuple of (summary, usage) if compression succeeds,
            (None, None) otherwise.

        Examples
        --------
        >>> summary, usage = await compactor.compress(context_manager)
        >>> if summary:
        ...     context_manager.replace_with_summary(summary)
        """
        messages: list[MessageDict] = context_manager.get_messages()

        if len(messages) < 3:
            logger.debug("Not enough messages to compress")
            return None, None

        compression_messages: list[MessageDict] = [
            {
                "role": "system",
                "content": get_compression_prompt(),
            },
            {
                "role": "user",
                "content": self._format_history_for_compaction(messages),
            },
        ]

        try:
            summary: str = ""
            usage: TokenUsage | None = None

            async for event in self.client.chat_completion(
                compression_messages,
                stream=False,
            ):
                if event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage
                    if event.text_delta:
                        summary = event.text_delta.content
                elif event.type == StreamEventType.ERROR:
                    logger.error(f"Compression error: {event.error}")
                    return None, None

            if not summary or not usage:
                logger.warning("Compression failed: empty summary or usage")
                return None, None

            logger.info(
                f"Compressed conversation history "
                f"({usage.total_tokens} tokens used for compression)",
            )
            return summary, usage

        except Exception as e:
            logger.error(f"Error during compression: {e}", exc_info=True)
            return None, None
