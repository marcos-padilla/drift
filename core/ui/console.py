"""
Console factory for creating rich console instances.

This module provides a factory function to create and configure
rich Console instances for consistent output formatting.
"""

from rich.console import Console


def get_console() -> Console:
    """
    Get a configured rich Console instance.

    Returns
    -------
    Console
        Configured rich Console instance with appropriate settings.

    Examples
    --------
    >>> console = get_console()
    >>> console.print("[bold]Hello[/bold]")
    """
    return Console()
