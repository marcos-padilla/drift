"""
Application-wide constants for the Drift framework.

This module defines constants used throughout the application to ensure
consistency and maintainability.
"""

from pathlib import Path

# Configuration file names
CONFIG_FILE_NAME: str = "config.toml"
AGENT_MD_FILE_NAME: str = "AGENT.MD"

# Application directories
APP_NAME: str = "ai-agent"
CONFIG_DIR_NAME: str = ".ai-agent"

# Default values
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_BASE_DELAY: float = 1.0
DEFAULT_RETRY_MAX_DELAY: float = 60.0

# Token estimation
DEFAULT_CHARS_PER_TOKEN: int = 4
MIN_TOKEN_COUNT: int = 1

# File operations
DEFAULT_BINARY_CHECK_CHUNK_SIZE: int = 8192
BINARY_MARKER: bytes = b"\x00"

# Path resolution
DEFAULT_ENCODING: str = "utf-8"
