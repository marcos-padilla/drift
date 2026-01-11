"""
ASCII art banner for Drift.

This module provides ASCII art banners and visual elements
for the Drift welcome screen.
"""

# Drift ASCII art banner
DRIFT_BANNER = """
╔═══════════════════════════════════════════════════════════╗
║                                                             ║
║     ██████╗ ██████╗ ██╗███████╗████████╗                    ║
║     ██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝                    ║
║     ██║  ██║██████╔╝██║█████╗     ██║                       ║
║     ██║  ██║██╔══██╗██║██╔══╝     ██║                       ║
║     ██████╔╝██║  ██║██║██║        ██║                       ║
║     ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝                       ║
║                                                             ║
║              AI Code Assistant Framework                    ║
║                                                             ║
╚═══════════════════════════════════════════════════════════╝
"""

# Compact version for smaller terminals
DRIFT_BANNER_COMPACT = """
┌─────────────────────────────────────────┐
│  ██████╗ ██████╗ ██╗███████╗████████╗  │
│  ██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝  │
│  ██║  ██║██████╔╝██║█████╗     ██║     │
│  ██║  ██║██╔══██╗██║██╔══╝     ██║     │
│  ██████╔╝██║  ██║██║██║        ██║     │
│  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝     │
│                                         │
│      AI Code Assistant Framework        │
└─────────────────────────────────────────┘
"""

# Minimal version
DRIFT_BANNER_MINIMAL = """
╔═══════════════════════════════════╗
║  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ║
║  ░  ██████╗ ██████╗ ██╗███████╗  ░  ║
║  ░  ██╔══██╗██╔══██╗██║██╔════╝  ░  ║
║  ░  ██║  ██║██████╔╝██║█████╗   ░  ║
║  ░  ██║  ██║██╔══██╗██║██╔══╝   ░  ║
║  ░  ██████╔╝██║  ██║██║██║      ░  ║
║  ░  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝      ░  ║
║  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ║
║                                     ║
║     AI Code Assistant Framework     ║
╚═══════════════════════════════════╝
"""


def get_banner(style: str = "default") -> str:
    """
    Get ASCII art banner for Drift.

    Parameters
    ----------
    style : str, default="default"
        Banner style: "default", "compact", or "minimal".

    Returns
    -------
    str
        ASCII art banner string.

    Examples
    --------
    >>> banner = get_banner("default")
    >>> print(banner)
    """
    if style == "compact":
        return DRIFT_BANNER_COMPACT
    elif style == "minimal":
        return DRIFT_BANNER_MINIMAL
    else:
        return DRIFT_BANNER
