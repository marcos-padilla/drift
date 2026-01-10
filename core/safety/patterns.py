"""
Command pattern definitions for safety assessment.

This module defines regex patterns for identifying dangerous and safe
commands to help make approval decisions.
"""

import re
from typing import Pattern

# Dangerous command patterns that should be rejected or require confirmation
DANGEROUS_PATTERNS: list[Pattern[str]] = [
    # File system destruction
    re.compile(r"rm\s+(-rf?|--recursive)\s+[/~]", re.IGNORECASE),
    re.compile(r"rm\s+-rf?\s+\*", re.IGNORECASE),
    re.compile(r"rmdir\s+[/~]", re.IGNORECASE),
    # Disk operations
    re.compile(r"dd\s+if=", re.IGNORECASE),
    re.compile(r"mkfs", re.IGNORECASE),
    re.compile(r"fdisk", re.IGNORECASE),
    re.compile(r"parted", re.IGNORECASE),
    # System control
    re.compile(r"shutdown", re.IGNORECASE),
    re.compile(r"reboot", re.IGNORECASE),
    re.compile(r"halt", re.IGNORECASE),
    re.compile(r"poweroff", re.IGNORECASE),
    re.compile(r"init\s+[06]", re.IGNORECASE),
    # Permission changes on root
    re.compile(r"chmod\s+(-R\s+)?777\s+[/~]", re.IGNORECASE),
    re.compile(r"chown\s+-R\s+.*\s+[/~]", re.IGNORECASE),
    # Network exposure
    re.compile(r"nc\s+-l", re.IGNORECASE),
    re.compile(r"netcat\s+-l", re.IGNORECASE),
    # Code execution from network
    re.compile(r"curl\s+.*\|\s*(bash|sh)", re.IGNORECASE),
    re.compile(r"wget\s+.*\|\s*(bash|sh)", re.IGNORECASE),
    # Fork bomb
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;", re.IGNORECASE),
]

# Safe command patterns that can be auto-approved
SAFE_PATTERNS: list[Pattern[str]] = [
    # Information commands
    re.compile(r"^(ls|dir|pwd|cd|echo|cat|head|tail|less|more|wc)(\s|$)", re.IGNORECASE),
    re.compile(r"^(find|locate|which|whereis|file|stat)(\s|$)", re.IGNORECASE),
    # Development tools (read-only)
    re.compile(r"^git\s+(status|log|diff|show|branch|remote|tag)(\s|$)", re.IGNORECASE),
    re.compile(r"^(npm|yarn|pnpm)\s+(list|ls|outdated)(\s|$)", re.IGNORECASE),
    re.compile(r"^pip\s+(list|show|freeze)(\s|$)", re.IGNORECASE),
    re.compile(r"^cargo\s+(tree|search)(\s|$)", re.IGNORECASE),
    # Text processing (usually safe)
    re.compile(r"^(grep|awk|sed|cut|sort|uniq|tr|diff|comm)(\s|$)", re.IGNORECASE),
    # System info
    re.compile(r"^(date|cal|uptime|whoami|id|groups|hostname|uname)(\s|$)", re.IGNORECASE),
    re.compile(r"^(env|printenv|set)$", re.IGNORECASE),
    # Process info
    re.compile(r"^(ps|top|htop|pgrep)(\s|$)", re.IGNORECASE),
]


def is_dangerous_command(command: str) -> bool:
    """
    Check if a command matches dangerous patterns.

    Parameters
    ----------
    command : str
        Command string to check.

    Returns
    -------
    bool
        True if the command matches any dangerous pattern.

    Examples
    --------
    >>> is_dangerous_command("rm -rf /")
    True
    >>> is_dangerous_command("ls -la")
    False
    """
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(command):
            return True
    return False


def is_safe_command(command: str) -> bool:
    """
    Check if a command matches safe patterns.

    Parameters
    ----------
    command : str
        Command string to check.

    Returns
    -------
    bool
        True if the command matches any safe pattern.

    Examples
    --------
    >>> is_safe_command("ls -la")
    True
    >>> is_safe_command("rm -rf /")
    False
    """
    for pattern in SAFE_PATTERNS:
        if pattern.search(command):
            return True
    return False
