"""
Main entry point for the Drift AI code assistant.

This module provides the command-line interface and main execution flow
for the Drift framework.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.config.loader import load_configuration
from core.exceptions import DriftError
from core.llm.client import LLMClient
from core.llm.models import StreamEventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """
    Configure logging for the application.

    Parameters
    ----------
    debug : bool, default=False
        Enable debug-level logging if True.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(level)
    logger.info(f"Logging configured at {'DEBUG' if debug else 'INFO'} level")


async def run_chat(
    messages: list[dict[str, str]],
    config_path: Path | None = None,
    stream: bool = True,
) -> None:
    """
    Run a chat completion with the LLM.

    Parameters
    ----------
    messages : list[dict[str, str]]
        List of messages in the conversation.
    config_path : Path | None, optional
        Path to configuration file. If None, uses default loading.
    stream : bool, default=True
        Whether to stream the response.

    Raises
    ------
    DriftError
        If configuration loading or chat completion fails.
    """
    try:
        # Load configuration
        cwd: Path | None = config_path.parent if config_path else None
        config = load_configuration(cwd=cwd)
        logger.info("Configuration loaded successfully")

        # Create and use client
        client = LLMClient(config)
        try:
            logger.info(f"Starting chat completion (stream={stream})")
            async for event in client.chat_completion(messages, stream=stream):
                if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
                    print(event.text_delta.content, end="", flush=True)
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    print()  # New line after completion
                    if event.usage:
                        logger.debug(
                            f"Token usage: {event.usage.total_tokens} total "
                            f"({event.usage.prompt_tokens} prompt, "
                            f"{event.usage.completion_tokens} completion)",
                        )
                elif event.type == StreamEventType.ERROR:
                    logger.error(f"Error in chat completion: {event.error}")
                    sys.exit(1)
        finally:
            await client.close()
            logger.debug("Client closed")

    except DriftError as e:
        logger.error(f"Drift error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Drift - AI Code Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file",
    )

    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming responses",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "message",
        nargs="?",
        help="Message to send to the assistant",
    )

    return parser.parse_args()


async def main() -> None:
    """
    Main entry point for the application.

    This function handles argument parsing, configuration loading, and
    execution of the chat completion.

    Raises
    ------
    SystemExit
        On error or successful completion.
    """
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(debug=args.debug)

    # Prepare messages
    if args.message:
        messages: list[dict[str, str]] = [
            {"role": "user", "content": args.message},
        ]
    else:
        # Default example message
        messages = [
            {"role": "user", "content": "What's up?"},
        ]

    # Run chat
    await run_chat(
        messages=messages,
        config_path=args.config,
        stream=not args.no_stream,
    )

    logger.info("Done")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
