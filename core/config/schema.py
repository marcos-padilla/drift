"""
Configuration schema definitions for the Drift framework.

This module defines the Pydantic models for configuration validation and
management, including model settings, shell environment policies, MCP server
configurations, and approval policies.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from core.exceptions import ValidationError


class ModelConfig(BaseModel):
    """
    Configuration for the LLM model.

    Parameters
    ----------
    name : str, default="gpt-4o"
        The name of the model to use.
    temperature : float, default=1.0
        Sampling temperature between 0.0 and 2.0.
    context_window : int, default=256000
        Maximum context window size in tokens.

    Examples
    --------
    >>> model = ModelConfig(name="gpt-4o", temperature=0.7)
    >>> model = ModelConfig()  # Uses defaults
    """

    name: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)",
    )
    context_window: int = Field(
        default=256_000,
        ge=1,
        description="Maximum context window size in tokens",
    )

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """
        Validate temperature is within acceptable range.

        Parameters
        ----------
        v : float
            Temperature value to validate.

        Returns
        -------
        float
            Validated temperature value.

        Raises
        ------
        ValidationError
            If temperature is outside the valid range.
        """
        if not 0.0 <= v <= 2.0:
            raise ValidationError(
                f"Temperature must be between 0.0 and 2.0, got {v}",
                field="temperature",
            )
        return v


class ShellEnvironmentPolicy(BaseModel):
    """
    Policy for shell environment variable handling.

    Parameters
    ----------
    ignore_default_excludes : bool, default=False
        Whether to ignore default exclusion patterns.
    exclude_patterns : list[str], default=["*KEY*", "*TOKEN*", "*SECRET*"]
        Patterns to exclude from environment variable exposure.
    set_vars : dict[str, str], default={}
        Environment variables to set explicitly.

    Examples
    --------
    >>> policy = ShellEnvironmentPolicy(
    ...     exclude_patterns=["*PASSWORD*"],
    ...     set_vars={"DEBUG": "true"}
    ... )
    """

    ignore_default_excludes: bool = Field(
        default=False,
        description="Ignore default exclusion patterns",
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*TOKEN*", "*SECRET*"],
        description="Patterns to exclude from environment",
    )
    set_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set",
    )


class MCPServerConfig(BaseModel):
    """
    Configuration for an MCP (Model Context Protocol) server.

    Supports both stdio (command-based) and HTTP/SSE (URL-based) transports.

    Parameters
    ----------
    enabled : bool, default=True
        Whether this MCP server is enabled.
    startup_timeout_sec : float, default=10.0
        Timeout in seconds for server startup.
    command : str | None, optional
        Command to run for stdio transport.
    args : list[str], default=[]
        Arguments for the command.
    env : dict[str, str], default={}
        Environment variables for the command.
    cwd : Path | None, optional
        Working directory for the command.
    url : str | None, optional
        URL for HTTP/SSE transport.

    Raises
    ------
    ValidationError
        If both command and url are provided, or neither is provided.

    Examples
    --------
    >>> # stdio transport
    >>> server = MCPServerConfig(
    ...     command="python",
    ...     args=["-m", "mcp_server"]
    ... )
    >>> # HTTP/SSE transport
    >>> server = MCPServerConfig(url="https://api.example.com/mcp")
    """

    enabled: bool = Field(default=True, description="Whether server is enabled")
    startup_timeout_sec: float = Field(
        default=10.0,
        ge=0.0,
        description="Startup timeout in seconds",
    )

    # stdio transport
    command: str | None = Field(
        default=None,
        description="Command for stdio transport",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )
    cwd: Path | None = Field(
        default=None,
        description="Working directory",
    )

    # http/sse transport
    url: str | None = Field(
        default=None,
        description="URL for HTTP/SSE transport",
    )

    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        """
        Validate that exactly one transport method is specified.

        Returns
        -------
        MCPServerConfig
            The validated configuration.

        Raises
        ------
        ValidationError
            If transport configuration is invalid.
        """
        has_command: bool = self.command is not None
        has_url: bool = self.url is not None

        if not has_command and not has_url:
            raise ValidationError(
                "MCP Server must have either 'command' (stdio) or 'url' (http/sse)",
                field="transport",
            )

        if has_command and has_url:
            raise ValidationError(
                "MCP Server cannot have both 'command' (stdio) and 'url' (http/sse)",
                field="transport",
            )

        return self


class ApprovalPolicy(str, Enum):
    """Policy for when to require user approval for actions."""

    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = "auto-edit"  # Fixed typo from original "auto-edut"
    NEVER = "never"
    YOLO = "yolo"


class HookTrigger(str, Enum):
    """Trigger points for hook execution."""

    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"


class HookConfig(BaseModel):
    """
    Configuration for a hook (script or command to run at specific points).

    Parameters
    ----------
    name : str
        Unique name for the hook.
    trigger : HookTrigger
        When to execute the hook.
    command : str | None, optional
        Command to execute (e.g., "python3 tests.py").
    script : str | None, optional
        Path to script file to execute (e.g., "*.sh").
    timeout_sec : float, default=30.0
        Maximum execution time in seconds.
    enabled : bool, default=True
        Whether the hook is enabled.

    Raises
    ------
    ValidationError
        If neither command nor script is provided.

    Examples
    --------
    >>> hook = HookConfig(
    ...     name="pre-test",
    ...     trigger=HookTrigger.BEFORE_TOOL,
    ...     command="python3 tests.py"
    ... )
    """

    name: str = Field(description="Hook name")
    trigger: HookTrigger = Field(description="When to execute hook")
    command: str | None = Field(
        default=None,
        description="Command to execute",
    )
    script: str | None = Field(
        default=None,
        description="Path to script file",
    )
    timeout_sec: float = Field(
        default=30.0,
        ge=0.0,
        description="Execution timeout in seconds",
    )
    enabled: bool = Field(
        default=True,
        description="Whether hook is enabled",
    )

    @model_validator(mode="after")
    def validate_hook(self) -> HookConfig:
        """
        Validate that either command or script is provided.

        Returns
        -------
        HookConfig
            The validated configuration.

        Raises
        ------
        ValidationError
            If neither command nor script is provided.
        """
        if not self.command and not self.script:
            raise ValidationError(
                "Hook must have either 'command' or 'script'",
                field="hook",
            )
        return self


class Configuration(BaseModel):
    """
    Main configuration model for the Drift framework.

    This model aggregates all configuration settings including model
    configuration, working directory, shell environment policies, hooks,
    approval policies, and MCP server configurations.

    Parameters
    ----------
    model : ModelConfig, optional
        Model configuration. Uses defaults if not provided.
    cwd : Path, optional
        Current working directory. Defaults to current directory.
    shell_environment : ShellEnvironmentPolicy, optional
        Shell environment policy. Uses defaults if not provided.
    hooks_enabled : bool, default=False
        Whether hooks are globally enabled.
    hooks : list[HookConfig], default=[]
        List of hook configurations.
    approval : ApprovalPolicy, default=ApprovalPolicy.ON_REQUEST
        Approval policy for actions.
    max_turns : int, default=100
        Maximum number of conversation turns.
    mcp_servers : dict[str, MCPServerConfig], default={}
        MCP server configurations keyed by server name.
    allowed_tools : list[str] | None, optional
        If set, only these tools will be available to the agent.
    developer_instructions : str | None, optional
        Instructions from project developers.
    user_instructions : str | None, optional
        Instructions from the user.
    debug : bool, default=False
        Enable debug mode.

    Examples
    --------
    >>> config = Configuration(
    ...     model=ModelConfig(name="gpt-4o", temperature=0.7),
    ...     approval=ApprovalPolicy.AUTO,
    ...     debug=True
    ... )
    """

    model: ModelConfig = Field(
        default_factory=ModelConfig,
        description="Model configuration",
    )
    cwd: Path = Field(
        default_factory=Path.cwd,
        description="Current working directory",
    )
    shell_environment: ShellEnvironmentPolicy = Field(
        default_factory=ShellEnvironmentPolicy,
        description="Shell environment policy",
    )
    hooks_enabled: bool = Field(
        default=False,
        description="Whether hooks are enabled",
    )
    hooks: list[HookConfig] = Field(
        default_factory=list,
        description="Hook configurations",
    )
    approval: ApprovalPolicy = Field(
        default=ApprovalPolicy.ON_REQUEST,
        description="Approval policy",
    )
    max_turns: int = Field(
        default=100,
        ge=1,
        description="Maximum conversation turns",
    )
    mcp_servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict,
        description="MCP server configurations",
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        description="Allowed tool names (None = all tools)",
    )
    developer_instructions: str | None = Field(
        default=None,
        description="Developer-provided instructions",
    )
    user_instructions: str | None = Field(
        default=None,
        description="User-provided instructions",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    @property
    def api_key(self) -> str | None:
        """
        Get the API key from environment variables.

        Returns
        -------
        str | None
            The API key if set, None otherwise.
        """
        return os.environ.get("API_KEY")

    @property
    def base_url(self) -> str | None:
        """
        Get the base URL from environment variables.

        Returns
        -------
        str | None
            The base URL if set, None otherwise.
        """
        return os.environ.get("BASE_URL")

    @property
    def model_name(self) -> str:
        """
        Get the model name.

        Returns
        -------
        str
            The model name.
        """
        return self.model.name

    @model_name.setter
    def model_name(self, value: str) -> None:
        """
        Set the model name.

        Parameters
        ----------
        value : str
            The new model name.
        """
        self.model.name = value

    @property
    def temperature(self) -> float:
        """
        Get the model temperature.

        Returns
        -------
        float
            The temperature value.
        """
        return self.model.temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        """
        Set the model temperature.

        Parameters
        ----------
        value : float
            The new temperature value (must be between 0.0 and 2.0).

        Raises
        ------
        ValidationError
            If temperature is outside valid range.
        """
        if not 0.0 <= value <= 2.0:
            raise ValidationError(
                f"Temperature must be between 0.0 and 2.0, got {value}",
                field="temperature",
            )
        self.model.temperature = value

    def validate(self) -> list[str]:
        """
        Validate the configuration and return any errors.

        Returns
        -------
        list[str]
            List of error messages. Empty list if configuration is valid.

        Examples
        --------
        >>> config = Configuration()
        >>> errors = config.validate()
        >>> if errors:
        ...     print("Configuration errors:", errors)
        """
        errors: list[str] = []

        if not self.api_key:
            errors.append("No API key found. Set API_KEY environment variable")

        if not self.cwd.exists():
            errors.append(f"Working directory does not exist: {self.cwd}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to a dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the configuration.

        Examples
        --------
        >>> config = Configuration()
        >>> config_dict = config.to_dict()
        """
        return self.model_dump(mode="json")
