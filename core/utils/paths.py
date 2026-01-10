"""
Path manipulation and validation utilities.

This module provides functions for resolving, validating, and manipulating
file paths with proper error handling and type safety.
"""

import logging
from pathlib import Path

from core.constants import DEFAULT_BINARY_CHECK_CHUNK_SIZE, DEFAULT_ENCODING
from core.exceptions import ValidationError
from core.types import PathLike

logger = logging.getLogger(__name__)


def resolve_path(base: PathLike, path: PathLike) -> Path:
    """
    Resolve a path relative to a base path.

    If the path is absolute, it is returned as-is (resolved). If it is
    relative, it is resolved relative to the base path.

    Parameters
    ----------
    base : PathLike
        Base path for resolving relative paths.
    path : PathLike
        Path to resolve (can be absolute or relative).

    Returns
    -------
    Path
        Resolved absolute path.

    Examples
    --------
    >>> base = Path("/home/user")
    >>> resolve_path(base, "documents/file.txt")
    PosixPath('/home/user/documents/file.txt')
    >>> resolve_path(base, "/absolute/path.txt")
    PosixPath('/absolute/path.txt')
    """
    path_obj: Path = Path(path)
    if path_obj.is_absolute():
        return path_obj.resolve()

    base_path: Path = Path(base).resolve()
    return base_path / path_obj


def display_path_relative_to_cwd(path: PathLike, cwd: Path | None = None) -> str:
    """
    Display a path relative to the current working directory.

    If the path is not within the CWD, returns the absolute path as a string.

    Parameters
    ----------
    path : PathLike
        Path to display.
    cwd : Path | None, optional
        Current working directory. If None, uses Path.cwd().

    Returns
    -------
    str
        Relative path string if within CWD, otherwise absolute path string.

    Examples
    --------
    >>> cwd = Path("/home/user/project")
    >>> display_path_relative_to_cwd("/home/user/project/src/main.py", cwd)
    'src/main.py'
    >>> display_path_relative_to_cwd("/other/path.txt", cwd)
    '/other/path.txt'
    """
    try:
        path_obj: Path = Path(path)
    except Exception as e:
        logger.warning(f"Invalid path format: {path}, returning as string: {e}")
        return str(path)

    if cwd is None:
        cwd = Path.cwd()

    try:
        return str(path_obj.relative_to(cwd))
    except ValueError:
        # Path is not relative to CWD
        return str(path_obj)


def ensure_parent_directory(path: PathLike) -> Path:
    """
    Ensure the parent directory of a path exists.

    Creates all necessary parent directories if they don't exist.

    Parameters
    ----------
    path : PathLike
        Path whose parent directory should be ensured.

    Returns
    -------
    Path
        The path object.

    Raises
    ------
    OSError
        If directory creation fails.

    Examples
    --------
    >>> path = ensure_parent_directory("/home/user/documents/file.txt")
    >>> # Creates /home/user/documents/ if it doesn't exist
    """
    path_obj: Path = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj


def is_binary_file(path: PathLike) -> bool:
    """
    Check if a file is binary by examining its content.

    A file is considered binary if it contains null bytes in the first
    chunk of data read.

    Parameters
    ----------
    path : PathLike
        Path to the file to check.

    Returns
    -------
    bool
        True if the file appears to be binary, False otherwise.

    Examples
    --------
    >>> is_binary_file("image.png")
    True
    >>> is_binary_file("script.py")
    False
    """
    path_obj: Path = Path(path)

    if not path_obj.exists() or not path_obj.is_file():
        return False

    try:
        with open(path_obj, "rb") as f:
            chunk: bytes = f.read(DEFAULT_BINARY_CHECK_CHUNK_SIZE)
            return b"\x00" in chunk
    except (OSError, IOError) as e:
        logger.warning(f"Failed to check if file is binary: {path_obj}: {e}")
        return False


def validate_path_within_base(path: PathLike, base: PathLike) -> Path:
    """
    Validate that a path is within a base directory.

    This is useful for security to ensure file operations stay within
    a designated workspace.

    Parameters
    ----------
    path : PathLike
        Path to validate.
    base : PathLike
        Base directory that the path must be within.

    Returns
    -------
    Path
        Resolved path if valid.

    Raises
    ------
    ValidationError
        If the path is outside the base directory.

    Examples
    --------
    >>> base = Path("/home/user/project")
    >>> validate_path_within_base("/home/user/project/src/file.py", base)
    PosixPath('/home/user/project/src/file.py')
    >>> validate_path_within_base("/etc/passwd", base)
    ValidationError: Path is outside base directory
    """
    path_obj: Path = resolve_path(base, path)
    base_path: Path = Path(base).resolve()

    try:
        path_obj.relative_to(base_path)
        return path_obj
    except ValueError:
        raise ValidationError(
            f"Path {path_obj} is outside base directory {base_path}",
            field="path",
        ) from None
