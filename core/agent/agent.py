"""
Main agent implementation for autonomous code assistance.

This module provides the core Agent class that orchestrates LLM interactions,
tool calls, context management, and safety checks.
"""

import logging
from typing import Any, AsyncGenerator, Awaitable, Callable

from core.agent.events import AgentEvent, AgentEventType
from core.agent.session import Session
from core.config.schema import Configuration
from core.llm.models import StreamEventType, ToolCall, ToolResultMessage
from core.prompts.builder import create_loop_breaker_prompt
from core.safety.models import ToolConfirmation

logger = logging.getLogger(__name__)

# Type alias for confirmation callback
ConfirmationCallback = Callable[[ToolConfirmation], bool | Awaitable[bool]]


class Agent:
    """
    Main agent for autonomous code assistance.

    This class orchestrates the agentic loop, managing LLM interactions,
    tool calls, context compression, and loop detection.

    Parameters
    ----------
    config : Configuration
        Configuration object with agent settings.
    confirmation_callback : ConfirmationCallback | None, optional
        Callback function for requesting user confirmation.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    session : Session | None
        Session instance (initialized in __aenter__).

    Examples
    --------
    >>> async with Agent(config) as agent:
    ...     async for event in agent.run("Fix the bug in main.py"):
    ...         if event.type == AgentEventType.TEXT_DELTA:
    ...             print(event.data["content"], end="")
    """

    def __init__(
        self,
        config: Configuration,
        confirmation_callback: ConfirmationCallback | None = None,
    ) -> None:
        self.config: Configuration = config
        self.session: Session | None = Session(self.config)
        if self.session:
            self.session.approval_manager.confirmation_callback = confirmation_callback

    async def run(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Run the agent with a user message.

        Parameters
        ----------
        message : str
            User message to process.

        Yields
        ------
        AgentEvent
            Events from agent execution including text deltas, tool calls,
            and completion events.

        Examples
        --------
        >>> async for event in agent.run("Hello!"):
        ...     if event.type == AgentEventType.TEXT_DELTA:
        ...         print(event.data["content"], end="")
        """
        if not self.session:
            raise RuntimeError("Agent session not initialized")

        await self.session.hook_system.trigger_before_agent(message)
        yield AgentEvent.agent_start(message)
        self.session.context_manager.add_user_message(message)

        final_response: str | None = None

        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        await self.session.hook_system.trigger_after_agent(
            message,
            final_response or "",
        )
        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Main agentic loop for processing turns.

        Yields
        ------
        AgentEvent
            Events from each turn of the agentic loop.
        """
        max_turns: int = self.config.max_turns

        if not self.session:
            raise RuntimeError("Agent session not initialized")

        for turn_num in range(max_turns):
            self.session.increment_turn()
            response_text: str = ""

            # Check for context overflow
            if self.session.context_manager.needs_compression():
                summary, usage = await self.session.chat_compactor.compress(
                    self.session.context_manager,
                )

                if summary:
                    self.session.context_manager.replace_with_summary(summary)
                    if usage:
                        self.session.context_manager.set_latest_usage(usage)
                        self.session.context_manager.add_usage(usage)

            tool_schemas = self.session.tool_registry.get_schemas()

            tool_calls: list[ToolCall] = []
            usage = None

            async for event in self.session.client.chat_completion(
                self.session.context_manager.get_messages(),
                tools=tool_schemas if tool_schemas else None,
            ):
                if event.type == StreamEventType.TEXT_DELTA:
                    if event.text_delta:
                        content: str = event.text_delta.content
                        response_text += content
                        yield AgentEvent.text_delta(content)
                elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                    if event.tool_call:
                        tool_calls.append(event.tool_call)
                elif event.type == StreamEventType.ERROR:
                    yield AgentEvent.agent_error(
                        event.error or "Unknown error occurred.",
                    )
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage

            self.session.context_manager.add_assistant_message(
                response_text or None,
                (
                    [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": str(tc.arguments),
                            },
                        }
                        for tc in tool_calls
                    ]
                    if tool_calls
                    else None
                ),
            )
            if response_text:
                yield AgentEvent.text_complete(response_text)
                self.session.loop_detector.record_action(
                    "response",
                    text=response_text,
                )

            if not tool_calls:
                if usage:
                    self.session.context_manager.set_latest_usage(usage)
                    self.session.context_manager.add_usage(usage)

                self.session.context_manager.prune_tool_outputs()
                return

            tool_call_results: list[ToolResultMessage] = []

            for tool_call in tool_calls:
                yield AgentEvent.tool_call_start(
                    tool_call.call_id,
                    tool_call.name,
                    tool_call.arguments,
                )

                self.session.loop_detector.record_action(
                    "tool_call",
                    tool_name=tool_call.name,
                    args=tool_call.arguments,
                )

                result = await self.session.tool_registry.invoke(
                    tool_call.name,
                    tool_call.arguments,
                    self.config.cwd,
                    self.session.hook_system,
                    self.session.approval_manager,
                )

                yield AgentEvent.tool_call_complete(
                    tool_call.call_id,
                    tool_call.name,
                    result,
                )

                tool_call_results.append(
                    ToolResultMessage(
                        tool_call_id=tool_call.call_id,
                        content=result.to_model_output(),
                        is_error=not result.success,
                    ),
                )

            for tool_result in tool_call_results:
                self.session.context_manager.add_tool_result(
                    tool_result.tool_call_id,
                    tool_result.content,
                )

            loop_detection_error = self.session.loop_detector.check_for_loop()
            if loop_detection_error:
                loop_prompt = create_loop_breaker_prompt(loop_detection_error)
                self.session.context_manager.add_user_message(loop_prompt)
                logger.warning(f"Loop detected: {loop_detection_error}")

            # Check for repeated errors
            if tool_call_results:
                error_count = sum(1 for r in tool_call_results if r.is_error)
                if error_count > 0:
                    logger.warning(f"Tool call errors in turn {turn_num + 1}: {error_count}")

            if usage:
                self.session.context_manager.set_latest_usage(usage)
                self.session.context_manager.add_usage(usage)

            self.session.context_manager.prune_tool_outputs()

        yield AgentEvent.agent_error(
            f"Maximum turns ({max_turns}) reached. Consider breaking the task into smaller steps.",
        )

    async def __aenter__(self) -> "Agent":
        """
        Async context manager entry.

        Returns
        -------
        Agent
            Self instance.

        Examples
        --------
        >>> async with Agent(config) as agent:
        ...     # Use agent
        """
        if self.session:
            await self.session.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Async context manager exit.

        Cleans up resources including closing the LLM client and
        shutting down MCP servers.

        Examples
        --------
        >>> async with Agent(config) as agent:
        ...     # Use agent
        >>> # Resources cleaned up automatically
        """
        if self.session:
            if self.session.client:
                await self.session.client.close()
            if self.session.mcp_manager:
                await self.session.mcp_manager.shutdown()
            self.session = None
            logger.debug("Agent resources cleaned up")
