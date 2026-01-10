"""
Context manager for conversation history and token tracking.

This module provides functionality to manage conversation context,
track token usage, and handle context compression when limits are reached.
"""

import logging
from datetime import datetime
from typing import Any

from core.config.schema import Configuration
from core.context.models import MessageItem
from core.llm.models import TokenUsage
from core.prompts.builder import PromptBuilder
from core.types import MessageDict
from core.utils.text import Tokenizer

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversation context and message history.

    This class tracks messages, token usage, and provides functionality
    for context compression and pruning when limits are reached.

    Parameters
    ----------
    config : Configuration
        Configuration object with model and context settings.
    user_memory : str | None, optional
        User-specific memory/context from previous interactions.
    tools : list[dict[str, Any]] | None, optional
        List of available tools with their metadata.

    Attributes
    ----------
    PRUNE_PROTECT_TOKENS : int
        Token threshold before which tool outputs are protected from pruning.
    PRUNE_MINIMUM_TOKENS : int
        Minimum tokens that must be pruned to trigger pruning operation.
    config : Configuration
        Configuration object.
    _messages : list[MessageItem]
        List of conversation messages.
    _latest_usage : TokenUsage
        Token usage from the most recent request.
    total_usage : TokenUsage
        Cumulative token usage across all requests.

    Examples
    --------
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> manager = ContextManager(config, user_memory="User prefers Python")
    >>> manager.add_user_message("Hello!")
    >>> messages = manager.get_messages()
    """

    PRUNE_PROTECT_TOKENS: int = 40_000
    PRUNE_MINIMUM_TOKENS: int = 20_000

    def __init__(
        self,
        config: Configuration,
        user_memory: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> None:
        self.config: Configuration = config
        self._prompt_builder: PromptBuilder = PromptBuilder(config)
        self._system_prompt: str = self._prompt_builder.build(
            user_memory=user_memory,
            tools=tools,
        )
        self._model_name: str = self.config.model_name
        self._tokenizer: Tokenizer = Tokenizer(model=self._model_name)
        self._messages: list[MessageItem] = []
        self._latest_usage: TokenUsage = TokenUsage()
        self.total_usage: TokenUsage = TokenUsage()

    @property
    def message_count(self) -> int:
        """
        Get the number of messages in the context.

        Returns
        -------
        int
            Number of messages.
        """
        return len(self._messages)

    def add_user_message(self, content: str) -> None:
        """
        Add a user message to the context.

        Parameters
        ----------
        content : str
            Content of the user message.

        Examples
        --------
        >>> manager.add_user_message("What is Python?")
        """
        item = MessageItem(
            role="user",
            content=content,
            token_count=self._tokenizer.count_tokens(content),
        )
        self._messages.append(item)
        logger.debug(f"Added user message ({item.token_count} tokens)")

    def add_assistant_message(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Add an assistant message to the context.

        Parameters
        ----------
        content : str
            Content of the assistant message.
        tool_calls : list[dict[str, Any]] | None, optional
            List of tool calls made by the assistant.

        Examples
        --------
        >>> manager.add_assistant_message(
        ...     "I'll help you with that.",
        ...     tool_calls=[{"function": {"name": "search", "arguments": "{}"}}]
        ... )
        """
        item = MessageItem(
            role="assistant",
            content=content or "",
            token_count=self._tokenizer.count_tokens(content or ""),
            tool_calls=tool_calls or [],
        )
        self._messages.append(item)
        logger.debug(
            f"Added assistant message ({item.token_count} tokens, "
            f"{len(tool_calls or [])} tool calls)",
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """
        Add a tool result message to the context.

        Parameters
        ----------
        tool_call_id : str
            ID of the tool call this result corresponds to.
        content : str
            Content of the tool result.

        Examples
        --------
        >>> manager.add_tool_result("call_123", '{"result": "success"}')
        """
        item = MessageItem(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            token_count=self._tokenizer.count_tokens(content),
        )
        self._messages.append(item)
        logger.debug(
            f"Added tool result ({item.token_count} tokens) for {tool_call_id}",
        )

    def get_messages(self) -> list[MessageDict]:
        """
        Get all messages in the format expected by the LLM API.

        Returns
        -------
        list[MessageDict]
            List of messages including system prompt and all conversation messages.

        Examples
        --------
        >>> messages = manager.get_messages()
        >>> # Returns list with system prompt and all messages
        """
        messages: list[MessageDict] = []

        if self._system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self._system_prompt,
                },
            )

        for item in self._messages:
            messages.append(item.to_dict())

        return messages

    def needs_compression(self) -> bool:
        """
        Check if the context needs compression based on token usage.

        Returns
        -------
        bool
            True if context usage exceeds 80% of the context window.

        Examples
        --------
        >>> if manager.needs_compression():
        ...     # Compress context
        """
        context_limit: int = self.config.model.context_window
        current_tokens: int = self._latest_usage.total_tokens

        return current_tokens > (context_limit * 0.8)

    def set_latest_usage(self, usage: TokenUsage) -> None:
        """
        Set the token usage from the most recent request.

        Parameters
        ----------
        usage : TokenUsage
            Token usage statistics from the latest request.

        Examples
        --------
        >>> usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        >>> manager.set_latest_usage(usage)
        """
        self._latest_usage = usage

    def add_usage(self, usage: TokenUsage) -> None:
        """
        Add token usage to the cumulative total.

        Parameters
        ----------
        usage : TokenUsage
            Token usage to add to the total.

        Examples
        --------
        >>> usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        >>> manager.add_usage(usage)
        """
        self.total_usage = self.total_usage + usage

    def replace_with_summary(self, summary: str) -> None:
        """
        Replace all messages with a summary for context restoration.

        This is used after context compression to restore conversation
        state with a compacted summary.

        Parameters
        ----------
        summary : str
            Compressed summary of the previous conversation.

        Examples
        --------
        >>> manager.replace_with_summary("Previous work: ...")
        """
        self._messages = []

        continuation_content: str = f"""# Context Restoration (Previous Session Compacted)

The previous conversation was compacted due to context length limits. Below is a detailed summary of the work done so far. 

**CRITICAL: Actions listed under "COMPLETED ACTIONS" are already done. DO NOT repeat them.**

---

{summary}

---

Resume work from where we left off. Focus ONLY on the remaining tasks."""

        summary_item = MessageItem(
            role="user",
            content=continuation_content,
            token_count=self._tokenizer.count_tokens(continuation_content),
        )
        self._messages.append(summary_item)

        ack_content: str = """I've reviewed the context from the previous session. I understand:
- The original goal and what was requested
- Which actions are ALREADY COMPLETED (I will NOT repeat these)
- The current state of the project
- What still needs to be done

I'll continue with the REMAINING tasks only, starting from where we left off."""
        ack_item = MessageItem(
            role="assistant",
            content=ack_content,
            token_count=self._tokenizer.count_tokens(ack_content),
        )
        self._messages.append(ack_item)

        continue_content: str = (
            "Continue with the REMAINING work only. Do NOT repeat any completed actions. "
            "Proceed with the next step as described in the context above."
        )

        continue_item = MessageItem(
            role="user",
            content=continue_content,
            token_count=self._tokenizer.count_tokens(continue_content),
        )
        self._messages.append(continue_item)

        logger.info("Replaced context with summary for restoration")

    def prune_tool_outputs(self) -> int:
        """
        Prune old tool output messages to save tokens.

        This method removes content from old tool results while preserving
        the message structure, helping to stay within token limits.

        Returns
        -------
        int
            Number of messages that were pruned.

        Examples
        --------
        >>> pruned_count = manager.prune_tool_outputs()
        >>> print(f"Pruned {pruned_count} tool outputs")
        """
        user_message_count: int = sum(
            (1 for msg in self._messages if msg.role == "user"),
        )

        if user_message_count < 2:
            return 0

        total_tokens: int = 0
        pruned_tokens: int = 0
        to_prune: list[MessageItem] = []

        for msg in reversed(self._messages):
            if msg.role == "tool" and msg.tool_call_id:
                if msg.pruned_at:
                    break

                tokens: int = msg.token_count or self._tokenizer.count_tokens(
                    msg.content,
                )
                total_tokens += tokens

                if total_tokens > self.PRUNE_PROTECT_TOKENS:
                    pruned_tokens += tokens
                    to_prune.append(msg)

        if pruned_tokens < self.PRUNE_MINIMUM_TOKENS:
            return 0

        pruned_count: int = 0

        for msg in to_prune:
            msg.content = "[Old tool result content cleared]"
            msg.token_count = self._tokenizer.count_tokens(msg.content)
            msg.pruned_at = datetime.now()
            pruned_count += 1

        logger.info(f"Pruned {pruned_count} tool output messages")
        return pruned_count

    def clear(self) -> None:
        """
        Clear all messages from the context.

        Examples
        --------
        >>> manager.clear()
        """
        self._messages = []
        logger.debug("Context cleared")
