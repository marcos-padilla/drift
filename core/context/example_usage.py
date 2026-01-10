"""
Example usage of context management features.

This module demonstrates how to use the context manager, loop detector,
and chat compactor together in a complete conversation flow.
"""

import asyncio
import logging

from core.config.loader import load_configuration
from core.context.compaction import ChatCompactor
from core.context.loop_detector import LoopDetector
from core.context.manager import ContextManager
from core.llm.client import LLMClient
from core.llm.models import StreamEventType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_conversation_with_context() -> None:
    """
    Example of a conversation using context management.

    This example demonstrates:
    - Creating a context manager
    - Adding messages to context
    - Detecting loops
    - Compressing context when needed
    - Using the context with LLM client
    """
    # Load configuration
    config = load_configuration()

    # Create context manager
    context_manager = ContextManager(
        config=config,
        user_memory="User prefers Python 3.12",
        tools=None,  # Add tools if available
    )

    # Create LLM client
    client = LLMClient(config)

    # Create loop detector
    loop_detector = LoopDetector()

    # Create chat compactor
    compactor = ChatCompactor(client)

    try:
        # Add initial user message
        context_manager.add_user_message("Help me write a Python function")

        # Get messages for LLM
        messages = context_manager.get_messages()

        # Process response
        async for event in client.chat_completion(messages, stream=True):
            if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
                print(event.text_delta.content, end="", flush=True)
            elif event.type == StreamEventType.MESSAGE_COMPLETE:
                print()  # New line

                # Record usage
                if event.usage:
                    context_manager.set_latest_usage(event.usage)
                    context_manager.add_usage(event.usage)

                # Check if compression is needed
                if context_manager.needs_compression():
                    logger.info("Context compression needed")
                    summary, usage = await compactor.compress(context_manager)
                    if summary:
                        context_manager.replace_with_summary(summary)
                        if usage:
                            context_manager.add_usage(usage)

                # Check for loops
                loop_description = loop_detector.check_for_loop()
                if loop_description:
                    logger.warning(f"Loop detected: {loop_description}")

        # Add assistant response to context (simplified - in real usage,
        # you'd parse the full response and tool calls)
        context_manager.add_assistant_message("I'll help you write a Python function")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_conversation_with_context())
