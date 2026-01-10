"""
Drift theme definition for rich console styling.

This module defines the color theme and styling for the Drift UI,
optimized for dark terminals with a minimal, clean design.
"""

from rich.theme import Theme

# Drift theme with dark color scheme
DRIFT_THEME = Theme(
    {
        # General styles
        "info": "cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "green",
        "dim": "dim",
        "muted": "grey50",
        "border": "grey35",
        "highlight": "bold cyan",
        # Role styles
        "user": "bright_blue bold",
        "assistant": "bright_white",  # Drift responses
        # Tool styles
        "tool": "bright_magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow",
        "tool.shell": "magenta",
        "tool.network": "bright_blue",
        "tool.memory": "green",
        "tool.mcp": "bright_cyan",
        # Code styles
        "code": "white",
    },
)
