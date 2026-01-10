"""
Text User Interface for the Drift framework.

This module provides a TUI class for handling user interactions,
displaying agent output, tool calls, and confirmation requests
with rich console formatting.
"""

import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.config.schema import Configuration
from core.safety.models import ToolConfirmation
from core.tools.models import ToolKind

logger = logging.getLogger(__name__)


class TUI:
    """
    Text User Interface for interactive agent sessions.

    This class handles all user-facing output including welcome messages,
    assistant responses, tool calls, and confirmation requests.

    Parameters
    ----------
    config : Configuration
        Configuration object.
    console : Console
        Rich console instance for output.

    Attributes
    ----------
    config : Configuration
        Configuration object.
    console : Console
        Rich console instance.
    _assistant_streaming : bool
        Whether assistant is currently streaming output.

    Examples
    --------
    >>> from core.ui.console import get_console
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> console = get_console()
    >>> tui = TUI(config, console)
    >>> tui.print_welcome("AI Agent", ["model: gpt-4o"])
    """

    def __init__(self, config: Configuration, console: Console) -> None:
        self.config: Configuration = config
        self.console: Console = console
        self._assistant_streaming: bool = False

    def print_welcome(
        self,
        title: str,
        lines: list[str] | None = None,
    ) -> None:
        """
        Print welcome message with title and information lines.

        Parameters
        ----------
        title : str
            Welcome title.
        lines : list[str] | None, optional
            Additional information lines to display.

        Examples
        --------
        >>> tui.print_welcome("AI Agent", ["model: gpt-4o", "cwd: /path"])
        """
        content: str = title
        if lines:
            content += "\n" + "\n".join(f"  {line}" for line in lines)

        self.console.print(Panel(content, title="[bold cyan]Welcome[/bold cyan]"))

    def begin_assistant(self) -> None:
        """
        Begin assistant output section.

        Examples
        --------
        >>> tui.begin_assistant()
        """
        if not self._assistant_streaming:
            self.console.print("\n[bold cyan][assistant][/bold cyan] ", end="")
            self._assistant_streaming = True

    def stream_assistant_delta(self, content: str) -> None:
        """
        Stream assistant text delta.

        Parameters
        ----------
        content : str
            Text content to stream.

        Examples
        --------
        >>> tui.begin_assistant()
        >>> tui.stream_assistant_delta("Hello")
        >>> tui.stream_assistant_delta(" world")
        """
        if not self._assistant_streaming:
            self.begin_assistant()
        self.console.print(content, end="", markup=False)

    def end_assistant(self) -> None:
        """
        End assistant output section.

        Examples
        --------
        >>> tui.end_assistant()
        """
        if self._assistant_streaming:
            self.console.print()  # New line
            self._assistant_streaming = False

    def tool_call_start(
        self,
        call_id: str,
        tool_name: str,
        tool_kind: str | None,
        arguments: dict[str, Any],
    ) -> None:
        """
        Display tool call start.

        Parameters
        ----------
        call_id : str
            Tool call ID.
        tool_name : str
            Name of the tool.
        tool_kind : str | None
            Kind of tool (read, write, shell, etc.).
        arguments : dict[str, Any]
            Tool arguments.

        Examples
        --------
        >>> tui.tool_call_start("call_123", "read_file", "read", {"path": "test.py"})
        """
        kind_display: str = f" [{tool_kind}]" if tool_kind else ""
        self.console.print(
            f"\n[dim][tool] Calling {tool_name}{kind_display}[/dim]",
        )
        if arguments:
            args_str: str = str(arguments)
            if len(args_str) > 100:
                args_str = args_str[:100] + "..."
            self.console.print(f"  [dim]args: {args_str}[/dim]")

    def tool_call_complete(
        self,
        call_id: str,
        tool_name: str,
        tool_kind: str | None,
        success: bool,
        output: str,
        error: str | None,
        metadata: dict[str, Any] | None,
        diff: str | None,
        truncated: bool,
        exit_code: int | None,
    ) -> None:
        """
        Display tool call completion result.

        Parameters
        ----------
        call_id : str
            Tool call ID.
        tool_name : str
            Name of the tool.
        tool_kind : str | None
            Kind of tool.
        success : bool
            Whether the tool call succeeded.
        output : str
            Tool output.
        error : str | None
            Error message if failed.
        metadata : dict[str, Any] | None
            Additional metadata.
        diff : str | None
            File diff if applicable.
        truncated : bool
            Whether output was truncated.
        exit_code : int | None
            Exit code for shell commands.

        Examples
        --------
        >>> tui.tool_call_complete(
        ...     "call_123", "read_file", "read", True, "file content", None, None, None, False, None
        ... )
        """
        status_color: str = "green" if success else "red"
        status_text: str = "✓" if success else "✗"
        kind_display: str = f" [{tool_kind}]" if tool_kind else ""

        self.console.print(
            f"  [{status_color}]{status_text}[/{status_color}] "
            f"{tool_name}{kind_display}",
        )

        if error:
            self.console.print(f"    [red]Error: {error}[/red]")

        if exit_code is not None and exit_code != 0:
            self.console.print(f"    [yellow]Exit code: {exit_code}[/yellow]")

        if truncated:
            self.console.print("    [dim]Output truncated[/dim]")

        if diff:
            # Show diff in a code block
            self.console.print("    [dim]Diff:[/dim]")
            self.console.print(f"    [code]{diff[:500]}[/code]")
            if len(diff) > 500:
                self.console.print("    [dim]... (diff truncated)[/dim]")

    def handle_confirmation(self, confirmation: ToolConfirmation) -> bool:
        """
        Handle user confirmation request.

        Parameters
        ----------
        confirmation : ToolConfirmation
            Confirmation request with tool details.

        Returns
        -------
        bool
            True if confirmed, False if rejected.

        Examples
        --------
        >>> confirmation = ToolConfirmation(...)
        >>> approved = tui.handle_confirmation(confirmation)
        """
        self.console.print("\n[bold yellow]Confirmation Required[/bold yellow]")
        self.console.print(f"Tool: [cyan]{confirmation.tool_name}[/cyan]")
        self.console.print(f"Description: {confirmation.description}")

        if confirmation.context.is_dangerous:
            self.console.print("[bold red]⚠ This action is flagged as dangerous[/bold red]")

        if confirmation.context.affected_paths:
            self.console.print("Affected paths:")
            for path in confirmation.context.affected_paths:
                self.console.print(f"  - {path}")

        if confirmation.context.command:
            self.console.print(f"Command: [code]{confirmation.context.command}[/code]")

        response: str = self.console.input("\n[bold]Approve? (y/n):[/bold] ").strip().lower()
        return response in ("y", "yes")

    def show_help(self) -> None:
        """
        Display help information with available commands.

        Examples
        --------
        >>> tui.show_help()
        """
        help_text: str = """
[bold]Available Commands:[/bold]

  /help              Show this help message
  /exit, /quit      Exit interactive mode
  /clear              Clear conversation and loop detector
  /config             Show current configuration
  /model [name]       Change or show model name
  /approval [policy]  Change or show approval policy
  /stats              Show session statistics
  /tools              List available tools
  /mcp                List MCP servers
  /save               Save current session
  /sessions           List saved sessions
  /resume <id>        Resume a saved session
  /checkpoint         Create a checkpoint
  /restore <id>       Restore from checkpoint
"""
        self.console.print(Panel(help_text, title="[bold cyan]Help[/bold cyan]"))
