"""
Main entry point for the Drift AI code assistant.

This module provides the command-line interface with interactive and
single-run modes, command handling, and session management.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

from core.agent.agent import Agent
from core.agent.events import AgentEventType
from core.agent.persistence import PersistenceManager, SessionSnapshot
from core.agent.session import Session
from core.config.loader import load_configuration
from core.config.schema import ApprovalPolicy, Configuration
from core.exceptions import ConfigurationError
from core.ui.console import get_console
from core.ui.tui import TUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

console = get_console()


class CLI:
    """
    Command-line interface for the Drift agent.

    This class provides both interactive and single-run modes for
    interacting with the agent, including command handling and
    session management.

    Parameters
    ----------
    config : Configuration
        Configuration object.

    Attributes
    ----------
    agent : Agent | None
        Current agent instance (set when running).
    config : Configuration
        Configuration object.
    tui : TUI
        Text user interface instance.

    Examples
    --------
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> cli = CLI(config)
    >>> await cli.run_single("Fix the bug")
    """

    def __init__(self, config: Configuration) -> None:
        self.agent: Agent | None = None
        self.config: Configuration = config
        self.tui: TUI = TUI(config, console)
        self.command_history: list[str] = []
        self.history_index: int = -1

    async def run_single(self, message: str) -> str | None:
        """
        Run agent with a single message (non-interactive mode).

        Parameters
        ----------
        message : str
            User message to process.

        Returns
        -------
        str | None
            Final response from agent, or None if error occurred.

        Examples
        --------
        >>> result = await cli.run_single("Hello!")
        """
        async with Agent(self.config) as agent:
            self.agent = agent
            return await self._process_message(message)

    async def run_interactive(self) -> str | None:
        """
        Run interactive mode with command loop.

        Returns
        -------
        str | None
            Final response, or None if exited.

        Examples
        --------
        >>> await cli.run_interactive()
        """
        self.tui.print_welcome(
            "Drift",
            lines=[
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )

        async with Agent(
            self.config,
            confirmation_callback=self.tui.handle_confirmation,
        ) as agent:
            self.agent = agent

            while True:
                try:
                    # Simple command history (up/down arrow support would need readline)
                    # Enhanced input prompt
                    user_input: str = console.input(
                        "\n[bold bright_blue]→[/bold bright_blue] ").strip()
                    if not user_input:
                        continue

                    # Add to history (skip duplicates of last command)
                    if not self.command_history or self.command_history[-1] != user_input:
                        self.command_history.append(user_input)
                        if len(self.command_history) > 100:
                            self.command_history.pop(0)
                    self.history_index = -1

                    if user_input.startswith("/"):
                        should_continue: bool = await self._handle_command(user_input)
                        if not should_continue:
                            break
                        continue

                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print(
                        "\n[dim italic]💡 Tip: Use /exit to quit[/dim italic]",
                    )
                except EOFError:
                    break

        # Enhanced goodbye message
        console.print()
        console.print(
            Panel(
                Text("👋 Thanks for using Drift!", style="bold bright_cyan"),
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 2),
            ),
        )
        return None

    def _get_tool_kind(self, tool_name: str) -> str | None:
        """
        Get the kind of a tool for display purposes.

        Parameters
        ----------
        tool_name : str
            Name of the tool.

        Returns
        -------
        str | None
            Tool kind value, or None if tool not found.

        Examples
        --------
        >>> kind = cli._get_tool_kind("read_file")
        >>> # Returns "read"
        """
        if not self.agent:
            return None

        tool = self.agent.session.tool_registry.get(tool_name)
        if not tool:
            return None

        return tool.kind.value

    async def _process_message(self, message: str) -> str | None:
        """
        Process a user message and handle agent events.

        Parameters
        ----------
        message : str
            User message to process.

        Returns
        -------
        str | None
            Final response from agent, or None if error occurred.

        Examples
        --------
        >>> response = await cli._process_message("Hello!")
        """
        if not self.agent:
            return None

        assistant_streaming: bool = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content: str = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_ERROR:
                error: str = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
                # Provide helpful suggestions for common errors
                if "Maximum turns" in error:
                    console.print(
                        "[dim]💡 Tip: Try breaking the task into smaller steps or use /clear to reset context[/dim]",
                    )
                elif "timeout" in error.lower():
                    console.print(
                        "[dim]💡 Tip: The operation timed out. Try with a smaller scope or increase timeout[/dim]",
                    )
                elif "not found" in error.lower():
                    console.print(
                        "[dim]💡 Tip: Check if the required tool or file exists[/dim]",
                    )
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name: str = event.data.get("name", "unknown")
                tool_kind: str | None = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get("exit_code"),
                )

        return final_response

    async def _handle_command(self, command: str) -> bool:
        """
        Handle slash commands in interactive mode.

        Parameters
        ----------
        command : str
            Command string (e.g., "/help", "/config", "/model gpt-4o").

        Returns
        -------
        bool
            True to continue, False to exit.

        Examples
        --------
        >>> should_continue = await cli._handle_command("/help")
        """
        if not self.agent:
            return True

        cmd: str = command.lower().strip()
        parts: list[str] = cmd.split(maxsplit=1)
        cmd_name: str = parts[0]
        cmd_args: str = parts[1] if len(parts) > 1 else ""

        if cmd_name == "/exit" or cmd_name == "/quit":
            return False
        elif command == "/help":
            self.tui.show_help()
        elif command == "/clear":
            self.agent.session.context_manager.clear()
            self.agent.session.loop_detector.clear()
            console.print("[success]Conversation cleared [/success]")
        elif command == "/config":
            console.print("\n[bold]Current Configuration[/bold]")
            console.print(f"  Model: {self.config.model_name}")
            console.print(f"  Temperature: {self.config.temperature}")
            console.print(f"  Approval: {self.config.approval.value}")
            console.print(f"  Working Dir: {self.config.cwd}")
            console.print(f"  Max Turns: {self.config.max_turns}")
            console.print(f"  Hooks Enabled: {self.config.hooks_enabled}")
        elif cmd_name == "/model":
            if cmd_args:
                self.config.model_name = cmd_args
                console.print(
                    f"[success]Model changed to: {cmd_args} [/success]")
            else:
                console.print(f"Current model: {self.config.model_name}")
        elif cmd_name == "/approval":
            if cmd_args:
                try:
                    approval = ApprovalPolicy(cmd_args)
                    self.config.approval = approval
                    console.print(
                        f"[success]Approval policy changed to: {cmd_args} [/success]",
                    )
                except ValueError:
                    valid_options: str = ", ".join(
                        p.value for p in ApprovalPolicy)
                    console.print(
                        f"[error]Incorrect approval policy: {cmd_args} [/error]",
                    )
                    console.print(f"Valid options: {valid_options}")
            else:
                console.print(
                    f"Current approval policy: {self.config.approval.value}",
                )
        elif cmd_name == "/stats":
            stats: dict[str, Any] = self.agent.session.get_stats()
            console.print("\n[bold]Session Statistics [/bold]")
            for key, value in stats.items():
                console.print(f"   {key}: {value}")
        elif cmd_name == "/tools":
            tools = self.agent.session.tool_registry.get_tools()
            console.print(f"\n[bold]Available tools ({len(tools)}) [/bold]")
            for tool in tools:
                console.print(f"  • {tool.name}")
        elif cmd_name == "/mcp":
            mcp_servers = self.agent.session.mcp_manager.get_all_servers()
            console.print(f"\n[bold]MCP Servers ({len(mcp_servers)}) [/bold]")
            for server in mcp_servers:
                status: str = server["status"]
                status_color: str = "green" if status == "connected" else "red"
                console.print(
                    f"  • {server['name']}: [{status_color}]{status}[/{status_color}] "
                    f"({server['tools']} tools)",
                )
        elif cmd_name == "/save":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_usage,
            )
            persistence_manager.save_session(session_snapshot)
            console.print(
                f"[success]Session saved: {self.agent.session.session_id}[/success]",
            )
        elif cmd_name == "/sessions":
            persistence_manager = PersistenceManager()
            sessions = persistence_manager.list_sessions()
            console.print("\n[bold]Saved Sessions[/bold]")
            for s in sessions:
                console.print(
                    f"  • {s['session_id']} "
                    f"(turns: {s['turn_count']}, updated: {s['updated_at']})",
                )
        elif cmd_name == "/resume":
            if not cmd_args:
                console.print("[error]Usage: /resume <session_id> [/error]")
            else:
                await self._resume_session(cmd_args)
        elif cmd_name == "/checkpoint":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_usage,
            )
            checkpoint_id: str = persistence_manager.save_checkpoint(
                session_snapshot)
            console.print(
                f"[success]Checkpoint created: {checkpoint_id}[/success]")
        elif cmd_name == "/restore":
            if not cmd_args:
                console.print(
                    "[error]Usage: /restore <checkpoint_id> [/error]")
            else:
                await self._restore_checkpoint(cmd_args)
        else:
            console.print(f"[error]Unknown command: {cmd_name}[/error]")

        return True

    async def _resume_session(self, session_id: str) -> None:
        """
        Resume a saved session.

        Parameters
        ----------
        session_id : str
            Session ID to resume.

        Examples
        --------
        >>> await cli._resume_session("session_123")
        """
        if not self.agent:
            return

        persistence_manager = PersistenceManager()
        snapshot = persistence_manager.load_session(session_id)
        if not snapshot:
            console.print("[error]Session does not exist [/error]")
            return

        # Create new session
        session = Session(config=self.config)
        await session.initialize()

        # Restore session metadata
        session.session_id = snapshot.session_id
        session.created_at = snapshot.created_at
        session.updated_at = snapshot.updated_at
        session.turn_count = snapshot.turn_count
        session.context_manager.total_usage = snapshot.total_usage

        # Restore messages
        for msg in snapshot.messages:
            role: str = msg.get("role", "")
            if role == "system":
                continue
            elif role == "user":
                session.context_manager.add_user_message(
                    msg.get("content", ""))
            elif role == "assistant":
                session.context_manager.add_assistant_message(
                    msg.get("content", ""),
                    msg.get("tool_calls"),
                )
            elif role == "tool":
                session.context_manager.add_tool_result(
                    msg.get("tool_call_id", ""),
                    msg.get("content", ""),
                )

        # Close old session resources
        await self.agent.session.client.close()
        await self.agent.session.mcp_manager.shutdown()

        # Replace session
        self.agent.session = session
        console.print(
            f"[success]Resumed session: {session.session_id}[/success]",
        )

    async def _restore_checkpoint(self, checkpoint_id: str) -> None:
        """
        Restore from a checkpoint.

        Parameters
        ----------
        checkpoint_id : str
            Checkpoint ID to restore.

        Examples
        --------
        >>> await cli._restore_checkpoint("checkpoint_123")
        """
        if not self.agent:
            return

        persistence_manager = PersistenceManager()
        snapshot = persistence_manager.load_checkpoint(checkpoint_id)
        if not snapshot:
            console.print("[error]Checkpoint does not exist [/error]")
            return

        # Create new session
        session = Session(config=self.config)
        await session.initialize()

        # Restore session metadata
        session.session_id = snapshot.session_id
        session.created_at = snapshot.created_at
        session.updated_at = snapshot.updated_at
        session.turn_count = snapshot.turn_count
        session.context_manager.total_usage = snapshot.total_usage

        # Restore messages
        for msg in snapshot.messages:
            role: str = msg.get("role", "")
            if role == "system":
                continue
            elif role == "user":
                session.context_manager.add_user_message(
                    msg.get("content", ""))
            elif role == "assistant":
                session.context_manager.add_assistant_message(
                    msg.get("content", ""),
                    msg.get("tool_calls"),
                )
            elif role == "tool":
                session.context_manager.add_tool_result(
                    msg.get("tool_call_id", ""),
                    msg.get("content", ""),
                )

        # Close old session resources
        await self.agent.session.client.close()
        await self.agent.session.mcp_manager.shutdown()

        # Replace session
        self.agent.session = session
        console.print(
            f"[success]Resumed session: {session.session_id}, "
            f"checkpoint: {checkpoint_id}[/success]",
        )


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
def main(
    prompt: str | None,
    cwd: Path | None,
) -> None:
    """
    Drift - AI Code Assistant.

    Run the agent in interactive mode or process a single prompt.
    """
    try:
        config: Configuration = load_configuration(cwd=cwd)
    except ConfigurationError as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Failed to load configuration: {e}")
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)

    # Validate configuration
    errors: list[str] = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)

    cli = CLI(config)

    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    load_dotenv()
    main()
