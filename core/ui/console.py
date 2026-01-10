"""
Console factory for creating rich console instances.

This module provides a factory function to create and configure
rich Console instances with the Drift theme for consistent output formatting.
"""

from rich.console import Console

from core.ui.theme import DRIFT_THEME

# Singleton console instance
_console: Console | None = None


def get_console() -> Console:
    """
    Get a configured rich Console instance with Drift theme.

    Returns a singleton console instance configured with the Drift theme
    and appropriate settings for dark terminals.

    Returns
    -------
    Console
        Configured rich Console instance with Drift theme.

    Examples
    --------
    >>> console = get_console()
    >>> console.print("[bold]Drift[/bold]")
    """
    global _console
    if _console is None:
        _console = Console(theme=DRIFT_THEME, highlight=False)
    return _console
