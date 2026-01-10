"""
Type definitions and aliases for the Drift framework.

This module provides common type aliases and type definitions used throughout
the codebase to ensure consistency and type safety.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from pathlib import Path

# Message types for LLM interactions
MessageRole = str  # "system", "user", "assistant", "tool"
MessageContent = Union[str, List[Dict[str, Any]]]
MessageDict = Dict[str, Any]

# Tool definitions
ToolDefinition = Dict[str, Any]
ToolDefinitions = List[ToolDefinition]

# Path types
PathLike = Union[str, Path]

# Configuration types
ConfigDict = Dict[str, Any]

# Token usage tracking
TokenCount = int

# Error context
ErrorDetails = Dict[str, Any]
