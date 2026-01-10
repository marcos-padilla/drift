"""
Configuration loader for the Drift framework.

This module provides functionality to load and merge configuration from
multiple sources including system-wide and project-specific configuration files.
"""

import logging
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None  # type: ignore[assignment,unused-ignore]

from core.config.schema import Configuration
from core.constants import (
    AGENT_MD_FILE_NAME,
    APP_NAME,
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
    DEFAULT_ENCODING,
)
from core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Get the system-wide configuration directory.

    Returns
    -------
    Path
        Path to the system configuration directory.

    Examples
    --------
    >>> config_dir = get_config_dir()
    >>> print(f"Config directory: {config_dir}")
    """
    return Path(user_config_dir(APP_NAME))


def get_data_dir() -> Path:
    """
    Get the system-wide data directory.

    Returns
    -------
    Path
        Path to the system data directory.

    Examples
    --------
    >>> data_dir = get_data_dir()
    >>> print(f"Data directory: {data_dir}")
    """
    return Path(user_data_dir(APP_NAME))


def get_system_config_path() -> Path:
    """
    Get the path to the system-wide configuration file.

    Returns
    -------
    Path
        Path to the system configuration file.

    Examples
    --------
    >>> config_path = get_system_config_path()
    >>> if config_path.exists():
    ...     print(f"Found config at: {config_path}")
    """
    return get_config_dir() / CONFIG_FILE_NAME


def _parse_toml(path: Path) -> dict[str, Any]:
    """
    Parse a TOML configuration file.

    Parameters
    ----------
    path : Path
        Path to the TOML file to parse.

    Returns
    -------
    dict[str, Any]
        Parsed configuration as a dictionary.

    Raises
    ------
    ConfigurationError
        If the file cannot be read or contains invalid TOML.

    Examples
    --------
    >>> config_dict = _parse_toml(Path("config.toml"))
    """
    if tomli is None:
        raise ConfigurationError(
            "TOML parsing not available. Install 'tomli' package.",
            config_file=str(path),
        )

    try:
        with open(path, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        if isinstance(e, (tomli.TOMLDecodeError, ValueError)):  # type: ignore[attr-defined]
            raise ConfigurationError(
                f"Invalid TOML in {path}: {e}",
                config_file=str(path),
                cause=e,
            ) from e
        raise ConfigurationError(
            f"Failed to read config file {path}: {e}",
            config_file=str(path),
            cause=e,
        ) from e


def _get_project_config(cwd: Path) -> Path | None:
    """
    Find project-specific configuration file.

    Searches for a configuration file in the `.ai-agent` directory
    within the current working directory.

    Parameters
    ----------
    cwd : Path
        Current working directory to search from.

    Returns
    -------
    Path | None
        Path to the project configuration file if found, None otherwise.

    Examples
    --------
    >>> project_config = _get_project_config(Path.cwd())
    >>> if project_config:
    ...     print(f"Found project config: {project_config}")
    """
    current: Path = cwd.resolve()
    agent_dir: Path = current / CONFIG_DIR_NAME

    if agent_dir.is_dir():
        config_file: Path = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file

    return None


def _get_agent_md_content(cwd: Path) -> str | None:
    """
    Read AGENT.MD file content if it exists.

    Parameters
    ----------
    cwd : Path
        Current working directory to search from.

    Returns
    -------
    str | None
        Content of AGENT.MD file if found, None otherwise.

    Examples
    --------
    >>> content = _get_agent_md_content(Path.cwd())
    >>> if content:
    ...     print("Found AGENT.MD instructions")
    """
    current: Path = cwd.resolve()

    if current.is_dir():
        agent_md_file: Path = current / AGENT_MD_FILE_NAME
        if agent_md_file.is_file():
            try:
                return agent_md_file.read_text(encoding=DEFAULT_ENCODING)
            except Exception as e:
                logger.warning(
                    f"Failed to read {agent_md_file}: {e}",
                    exc_info=True,
                )
                return None

    return None


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Values from `override` take precedence over `base`. Nested dictionaries
    are merged recursively.

    Parameters
    ----------
    base : dict[str, Any]
        Base dictionary to merge into.
    override : dict[str, Any]
        Dictionary with values that override base.

    Returns
    -------
    dict[str, Any]
        Merged dictionary.

    Examples
    --------
    >>> base = {"a": 1, "b": {"c": 2}}
    >>> override = {"b": {"d": 3}, "e": 4}
    >>> merged = _merge_dicts(base, override)
    >>> # Result: {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
    """
    result: dict[str, Any] = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def load_configuration(cwd: Path | None = None) -> Configuration:
    """
    Load configuration from system and project sources.

    This function loads configuration in the following order:
    1. System-wide configuration (if exists)
    2. Project-specific configuration (if exists, overrides system)
    3. AGENT.MD file content (if exists, added as developer_instructions)
    4. Environment variables (for API key, base URL, etc.)

    Parameters
    ----------
    cwd : Path | None, optional
        Current working directory. If None, uses the current directory.

    Returns
    -------
    Configuration
        Loaded and validated configuration object.

    Raises
    ------
    ConfigurationError
        If configuration loading or validation fails.

    Examples
    --------
    >>> # Load from current directory
    >>> config = load_configuration()
    >>> # Load from specific directory
    >>> config = load_configuration(Path("/path/to/project"))
    """
    cwd = cwd or Path.cwd()
    system_path: Path = get_system_config_path()

    config_dict: dict[str, Any] = {}

    # Load system-wide configuration
    if system_path.is_file():
        try:
            config_dict = _parse_toml(system_path)
            logger.debug(f"Loaded system config from {system_path}")
        except ConfigurationError as e:
            logger.warning(
                f"Skipping invalid system config {system_path}: {e}",
            )

    # Load project-specific configuration (overrides system)
    project_path: Path | None = _get_project_config(cwd)
    if project_path:
        try:
            project_config_dict: dict[str, Any] = _parse_toml(project_path)
            config_dict = _merge_dicts(config_dict, project_config_dict)
            logger.debug(f"Loaded project config from {project_path}")
        except ConfigurationError as e:
            logger.warning(
                f"Skipping invalid project config {project_path}: {e}",
            )

    # Set working directory if not already set
    if "cwd" not in config_dict:
        config_dict["cwd"] = str(cwd)

    # Load AGENT.MD file if it exists
    if "developer_instructions" not in config_dict:
        agent_md_content: str | None = _get_agent_md_content(cwd)
        if agent_md_content:
            config_dict["developer_instructions"] = agent_md_content
            logger.debug(f"Loaded AGENT.MD from {cwd}")

    # Create and validate configuration
    try:
        config: Configuration = Configuration(**config_dict)
    except Exception as e:
        raise ConfigurationError(
            f"Invalid configuration: {e}",
            cause=e,
        ) from e

    # Run additional validation
    validation_errors: list[str] = config.validate()
    if validation_errors:
        error_msg: str = "Configuration validation failed:\n" + "\n".join(
            f"  - {err}" for err in validation_errors
        )
        raise ConfigurationError(error_msg)

    logger.info(f"Configuration loaded successfully from {cwd}")
    return config
