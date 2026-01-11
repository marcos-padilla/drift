"""
Drift theme definition for rich console styling.

This module defines the color theme and styling for the Drift UI,
optimized for dark terminals with a minimal, clean design.
"""

from rich.theme import Theme

# Drift theme with dark color scheme - enhanced
DRIFT_THEME = Theme(
    {
        # General styles
        "info": "bright_cyan",
        "warning": "bright_yellow",
        "error": "bright_red bold",
        "success": "bright_green",
        "dim": "dim",
        "muted": "grey50",
        "border": "cyan",
        "highlight": "bold bright_cyan",
        # Role styles
        "user": "bright_blue bold",
        "assistant": "bright_white",  # Drift responses
        # Tool styles - enhanced with better colors
        "tool": "bright_magenta bold",
        "tool.read": "bright_cyan",
        "tool.write": "bright_yellow",
        "tool.shell": "bright_magenta",
        "tool.network": "bright_blue",
        "tool.memory": "bright_green",
        "tool.mcp": "bright_cyan",
        # Code styles
        "code": "white",
    },
)
