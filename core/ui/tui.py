"""
Text User Interface for the Drift framework.

This module provides a TUI class for handling user interactions,
displaying agent output, tool calls, and confirmation requests
with rich console formatting and a minimal, clean design.
"""

import logging
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from core.config.schema import Configuration
from core.safety.models import ToolConfirmation
from core.ui.formatters import (
    format_generic_output,
    format_grep_output,
    format_glob_output,
    format_list_dir_output,
    format_memory_output,
    format_read_file_output,
    format_shell_output,
    format_tool_arguments_table,
    format_todos_output,
    format_web_fetch_output,
    format_web_search_output,
    format_write_file_output,
)

logger = logging.getLogger(__name__)

# Maximum tokens for tool output blocks
MAX_BLOCK_TOKENS: int = 2500


class TUI:
    """
    Text User Interface for interactive Drift sessions.

    This class handles all user-facing output including welcome messages,
    Drift responses, tool calls, and confirmation requests with a minimal,
    clean design optimized for dark terminals.

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
    _assistant_stream_open : bool
        Whether assistant is currently streaming output.
    _tool_args_by_call_id : dict[str, dict[str, Any]]
        Dictionary storing tool arguments by call ID for completion display.
    cwd : Path
        Current working directory.

    Examples
    --------
    >>> from core.ui.console import get_console
    >>> from core.config.loader import load_configuration
    >>> config = load_configuration()
    >>> console = get_console()
    >>> tui = TUI(config, console)
    >>> tui.print_welcome("Drift", ["model: gpt-4o"])
    """

    def __init__(self, config: Configuration, console: Console) -> None:
        self.config: Configuration = config
        self.console: Console = console
        self._assistant_stream_open: bool = False
        self._tool_args_by_call_id: dict[str, dict[str, Any]] = {}
        self.cwd: Path = config.cwd

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
        >>> tui.print_welcome("Drift", ["model: gpt-4o", "cwd: /path"])
        """
        body: str = "\n".join(lines) if lines else ""
        self.console.print(
            Panel(
                Text(body, style="code"),
                title=Text(title, style="highlight"),
                title_align="left",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            ),
        )

    def begin_assistant(self) -> None:
        """
        Begin assistant output section.

        Examples
        --------
        >>> tui.begin_assistant()
        """
        self.console.print()
        self.console.print(Rule(Text("Drift", style="assistant")))
        self._assistant_stream_open = True

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
        self.console.print(content, end="", markup=False)

    def end_assistant(self) -> None:
        """
        End assistant output section.

        Examples
        --------
        >>> tui.end_assistant()
        """
        if self._assistant_stream_open:
            self.console.print()
        self._assistant_stream_open = False

    def tool_call_start(
        self,
        call_id: str,
        name: str,
        tool_kind: str | None,
        arguments: dict[str, Any],
    ) -> None:
        """
        Display tool call start.

        Parameters
        ----------
        call_id : str
            Tool call ID.
        name : str
            Name of the tool.
        tool_kind : str | None
            Kind of tool (read, write, shell, etc.).
        arguments : dict[str, Any]
            Tool arguments.

        Examples
        --------
        >>> tui.tool_call_start("call_123", "read_file", "read", {"path": "test.py"})
        """
        # Store arguments for completion display
        self._tool_args_by_call_id[call_id] = arguments

        border_style: str = f"tool.{tool_kind}" if tool_kind else "tool"

        title = Text.assemble(
            ("⏺ ", "muted"),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        # Display paths relative to CWD
        display_args: dict[str, Any] = dict(arguments)
        for key in ("path", "cwd"):
            val = display_args.get(key)
            if isinstance(val, str) and self.cwd:
                from core.ui.helpers import display_path_rel_to_cwd

                display_args[key] = display_path_rel_to_cwd(val, self.cwd)

        panel = Panel(
            (
                format_tool_arguments_table(name, display_args, self.cwd)
                if display_args
                else Text("(no args)", style="muted")
            ),
            title=title,
            title_align="left",
            subtitle=Text("running", style="muted"),
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print()
        self.console.print(panel)

    def tool_call_complete(
        self,
        call_id: str,
        name: str,
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
        name : str
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
        border_style: str = f"tool.{tool_kind}" if tool_kind else "tool"
        status_icon: str = "✓" if success else "✗"
        status_style: str = "success" if success else "error"

        title = Text.assemble(
            (f"{status_icon} ", status_style),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        args: dict[str, Any] = self._tool_args_by_call_id.get(call_id, {})

        # Format output based on tool type
        blocks: list[Any] = []

        if name == "read_file" and success:
            blocks.append(
                format_read_file_output(
                    name,
                    output,
                    metadata,
                    self.cwd,
                    self.config.model_name,
                ),
            )
        elif name in {"write_file", "edit"} and success and diff:
            blocks.append(
                format_write_file_output(
                    name,
                    output,
                    diff,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "shell" and success:
            blocks.append(
                format_shell_output(
                    name,
                    output,
                    args,
                    exit_code,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "list_dir" and success:
            blocks.append(
                format_list_dir_output(
                    name,
                    output,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "grep" and success:
            blocks.append(
                format_grep_output(
                    name,
                    output,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "glob" and success:
            blocks.append(
                format_glob_output(
                    name,
                    output,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "web_search" and success:
            blocks.append(
                format_web_search_output(
                    name,
                    output,
                    args,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "web_fetch" and success:
            blocks.append(
                format_web_fetch_output(
                    name,
                    output,
                    args,
                    metadata,
                    self.config.model_name,
                ),
            )
        elif name == "todos" and success:
            blocks.append(
                format_todos_output(
                    name,
                    output,
                    self.config.model_name,
                ),
            )
        elif name == "memory" and success:
            blocks.append(
                format_memory_output(
                    name,
                    output,
                    args,
                    metadata,
                    self.config.model_name,
                ),
            )
        else:
            blocks.append(
                format_generic_output(
                    name,
                    output,
                    error,
                    success,
                    self.config.model_name,
                ),
            )

        # Add error recovery suggestions for failed operations
        if not success and error:
            error_lower: str = error.lower()
            suggestions: list[str] = []
            if "not found" in error_lower:
                suggestions.append("Check if the file/path exists")
            elif "permission" in error_lower:
                suggestions.append("Check file permissions")
            elif "timeout" in error_lower:
                suggestions.append("Operation timed out - try with smaller scope")
            elif "validation" in error_lower:
                suggestions.append("Check parameter format and requirements")

            if suggestions:
                suggestion_text = Text("💡 Suggestions: ", style="dim")
                suggestion_text.append("; ".join(suggestions), style="dim italic")
                blocks.append(suggestion_text)

        if truncated:
            blocks.append(
                Text("note: tool output was truncated", style="warning"))

        panel = Panel(
            Group(*blocks),
            title=title,
            title_align="left",
            subtitle=Text("done" if success else "failed", style=status_style),
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print()
        self.console.print(panel)

    def handle_confirmation(self, confirmation: ToolConfirmation) -> bool:
        """
        Handle user confirmation request.

        Parameters
        ----------
        confirmation : ToolConfirmation
            Confirmation request with tool details (from core.safety.models).

        Returns
        -------
        bool
            True if confirmed, False if rejected.

        Examples
        --------
        >>> confirmation = ToolConfirmation(...)
        >>> approved = tui.handle_confirmation(confirmation)
        """
        output: list[Any] = [
            Text(confirmation.tool_name, style="tool"),
            Text(confirmation.description, style="code"),
        ]

        if confirmation.context.command:
            output.append(
                Text(f"$ {confirmation.context.command}", style="warning"))

        if confirmation.context.affected_paths:
            paths_text: str = "\n".join(
                str(p) for p in confirmation.context.affected_paths)
            output.append(
                Text(f"Affected paths:\n{paths_text}", style="muted"))

        if confirmation.context.is_dangerous:
            output.append(
                Text("⚠ This action is flagged as dangerous", style="error"))

        self.console.print()
        self.console.print(
            Panel(
                Group(*output),
                title=Text("Approval required", style="warning"),
                title_align="left",
                border_style="warning",
                box=box.ROUNDED,
                padding=(1, 2),
            ),
        )

        response: str = Prompt.ask(
            "\nApprove?",
            choices=["y", "n", "yes", "no"],
            default="n",
        )

        return response.lower() in {"y", "yes"}

    def show_help(self) -> None:
        """
        Display help information with available commands.

        Examples
        --------
        >>> tui.show_help()
        """
        help_text: str = """
## Commands

- `/help` - Show this help
- `/exit` or `/quit` - Exit Drift
- `/clear` - Clear conversation history
- `/config` - Show current configuration
- `/model <name>` - Change the model
- `/approval <mode>` - Change approval mode
- `/stats` - Show session statistics
- `/tools` - List available tools
- `/mcp` - Show MCP server status
- `/save` - Save current session
- `/checkpoint` - Create a checkpoint
- `/restore <checkpoint_id>` - Restore a checkpoint
- `/sessions` - List saved sessions
- `/resume <session_id>` - Resume a saved session

## Tips

- Just type your message to chat with Drift
- Drift can read, write, and execute code
- Some operations require approval (can be configured)
"""
        self.console.print(Markdown(help_text))
