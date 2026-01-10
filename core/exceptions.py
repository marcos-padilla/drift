"""
Exception hierarchy for the Drift framework.

This module defines a comprehensive exception hierarchy with proper error
codes, context, and serialization capabilities for better error handling
and debugging.
"""

from typing import Any, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for categorizing exceptions."""

    UNKNOWN = "UNKNOWN"
    CONFIGURATION = "CONFIGURATION"
    CONNECTION = "CONNECTION"
    API = "API"
    VALIDATION = "VALIDATION"
    IO = "IO"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"


class DriftError(Exception):
    """
    Base exception class for all Drift framework errors.

    This exception provides a structured way to handle errors with error codes,
    detailed context, and proper exception chaining.

    Parameters
    ----------
    message : str
        Human-readable error message.
    error_code : ErrorCode, default=ErrorCode.UNKNOWN
        Categorization code for the error.
    details : dict[str, Any] | None, optional
        Additional context about the error.
    cause : Exception | None, optional
        The underlying exception that caused this error.

    Attributes
    ----------
    message : str
        The error message.
    error_code : ErrorCode
        The error code categorizing this error.
    details : dict[str, Any]
        Additional error context.
    cause : Exception | None
        The underlying exception that caused this error.

    Examples
    --------
    >>> raise DriftError("Something went wrong", ErrorCode.UNKNOWN)
    >>> raise DriftError(
    ...     "Invalid configuration",
    ...     ErrorCode.CONFIGURATION,
    details={"config_key": "api_key"}
    ... )
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.error_code: ErrorCode = error_code
        self.details: dict[str, Any] = details or {}
        self.cause: Exception | None = cause

    def __str__(self) -> str:
        """
        Return a string representation of the error.

        Returns
        -------
        str
            Formatted error string with message, details, and cause.
        """
        parts: list[str] = [f"[{self.error_code.value}] {self.message}"]
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"Details: {detail_str}")
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """
        Return a detailed representation of the error.

        Returns
        -------
        str
            Detailed error representation.
        """
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code.value!r}, "
            f"details={self.details!r}, "
            f"cause={self.cause!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the error to a dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the error with all context.
        """
        result: dict[str, Any] = {
            "type": self.__class__.__name__,
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }
        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }
        return result


class ConfigurationError(DriftError):
    """
    Exception raised for configuration-related errors.

    This exception is used when there are issues loading, parsing, or
    validating configuration files or settings.

    Parameters
    ----------
    message : str
        Human-readable error message.
    config_key : str | None, optional
        The configuration key that caused the error.
    config_file : str | None, optional
        The configuration file path where the error occurred.
    details : dict[str, Any] | None, optional
        Additional context about the error.
    cause : Exception | None, optional
        The underlying exception that caused this error.

    Attributes
    ----------
    config_key : str | None
        The configuration key that caused the error.
    config_file : str | None
        The configuration file path where the error occurred.

    Examples
    --------
    >>> raise ConfigurationError(
    ...     "Invalid API key format",
    ...     config_key="api_key",
    ...     config_file="config.toml"
    ... )
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(
            message,
            error_code=ErrorCode.CONFIGURATION,
            details=details,
            cause=cause,
        )
        self.config_key: str | None = config_key
        self.config_file: str | None = config_file


class ConnectionError(DriftError):
    """
    Exception raised for connection-related errors.

    This exception is used when there are issues connecting to external
    services or APIs.

    Parameters
    ----------
    message : str
        Human-readable error message.
    endpoint : str | None, optional
        The endpoint that failed to connect.
    details : dict[str, Any] | None, optional
        Additional context about the error.
    cause : Exception | None, optional
        The underlying exception that caused this error.

    Examples
    --------
    >>> raise ConnectionError(
    ...     "Failed to connect to API",
    ...     endpoint="https://api.example.com"
    ... )
    """

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if endpoint:
            details["endpoint"] = endpoint
        super().__init__(
            message,
            error_code=ErrorCode.CONNECTION,
            details=details,
            cause=cause,
        )
        self.endpoint: str | None = endpoint


class APIError(DriftError):
    """
    Exception raised for API-related errors.

    This exception is used when there are issues with API calls, such as
    invalid responses or API-specific errors.

    Parameters
    ----------
    message : str
        Human-readable error message.
    status_code : int | None, optional
        HTTP status code if applicable.
    details : dict[str, Any] | None, optional
        Additional context about the error.
    cause : Exception | None, optional
        The underlying exception that caused this error.

    Examples
    --------
    >>> raise APIError(
    ...     "Invalid API response",
    ...     status_code=500
    ... )
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if status_code is not None:
            details["status_code"] = status_code
        super().__init__(
            message,
            error_code=ErrorCode.API,
            details=details,
            cause=cause,
        )
        self.status_code: int | None = status_code


class RateLimitError(APIError):
    """
    Exception raised when rate limits are exceeded.

    This exception is a specialized API error for rate limiting scenarios.

    Parameters
    ----------
    message : str
        Human-readable error message.
    retry_after : float | None, optional
        Suggested time in seconds to wait before retrying.
    details : dict[str, Any] | None, optional
        Additional context about the error.
    cause : Exception | None, optional
        The underlying exception that caused this error.

    Examples
    --------
    >>> raise RateLimitError(
    ...     "Rate limit exceeded",
    ...     retry_after=60.0
    ... )
    """

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(
            message,
            status_code=429,
            details=details,
            cause=cause,
        )
        self.retry_after: float | None = retry_after


class ValidationError(DriftError):
    """
    Exception raised for validation errors.

    This exception is used when data validation fails, such as invalid
    input parameters or malformed data structures.

    Parameters
    ----------
    message : str
        Human-readable error message.
    field : str | None, optional
        The field that failed validation.
    details : dict[str, Any] | None, optional
        Additional context about the error.
    cause : Exception | None, optional
        The underlying exception that caused this error.

    Examples
    --------
    >>> raise ValidationError(
    ...     "Invalid temperature value",
    ...     field="temperature"
    ... )
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message,
            error_code=ErrorCode.VALIDATION,
            details=details,
            cause=cause,
        )
        self.field: str | None = field
