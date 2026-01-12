"""
Ollama integration for local model management.

This module provides functionality to interact with Ollama's local API
for listing models and getting model information.
"""

import logging
from typing import Any

import httpx
from pydantic import BaseModel

from core.exceptions import ConnectionError

logger = logging.getLogger(__name__)

# Default Ollama API endpoint
OLLAMA_BASE_URL: str = "http://localhost:11434"


class OllamaModelInfo(BaseModel):
    """
    Information about an Ollama model.

    Parameters
    ----------
    name : str
        Model name.
    size : int
        Model size in bytes.
    modified_at : str
        Last modification timestamp.

    Examples
    --------
    >>> model = OllamaModelInfo(name="gpt-oss:20b", size=13958643712)
    """

    name: str
    size: int
    modified_at: str


def list_ollama_models(
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = 5.0,
) -> list[OllamaModelInfo]:
    """
    List all available Ollama models.

    Parameters
    ----------
    base_url : str, default="http://localhost:11434"
        Ollama server base URL.
    timeout : float, default=5.0
        Request timeout in seconds.

    Returns
    -------
    list[OllamaModelInfo]
        List of available models.

    Raises
    ------
    ConnectionError
        If Ollama server is not running or unreachable.

    Examples
    --------
    >>> models = list_ollama_models()
    >>> for model in models:
    ...     print(f"{model.name}: {model.size / 1024**3:.1f} GB")
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            models: list[OllamaModelInfo] = []
            for model_data in data.get("models", []):
                model_info = OllamaModelInfo(
                    name=model_data.get("name", ""),
                    size=model_data.get("size", 0),
                    modified_at=model_data.get("modified_at", ""),
                )
                models.append(model_info)

            return models
    except httpx.ConnectError as e:
        raise ConnectionError(
            f"Could not connect to Ollama at {base_url}. "
            "Make sure Ollama is running.",
            cause=e,
        ) from e
    except httpx.HTTPStatusError as e:
        raise ConnectionError(
            f"Ollama API error: {e.response.status_code}",
            cause=e,
        ) from e
    except Exception as e:
        logger.exception(f"Error listing Ollama models: {e}")
        raise ConnectionError(
            f"Failed to list Ollama models: {e}",
            cause=e,
        ) from e


def get_ollama_model_info(
    model_name: str,
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = 5.0,
) -> OllamaModelInfo | None:
    """
    Get information about a specific Ollama model.

    Parameters
    ----------
    model_name : str
        Name of the model to query.
    base_url : str, default="http://localhost:11434"
        Ollama server base URL.
    timeout : float, default=5.0
        Request timeout in seconds.

    Returns
    -------
    OllamaModelInfo | None
        Model information if found, None otherwise.

    Examples
    --------
    >>> info = get_ollama_model_info("gpt-oss:20b")
    >>> if info:
    ...     print(f"Model size: {info.size / 1024**3:.1f} GB")
    """
    models = list_ollama_models(base_url, timeout)
    for model in models:
        if model.name == model_name:
            return model
    return None


def check_ollama_connection(
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = 5.0,
) -> bool:
    """
    Check if Ollama server is running and accessible.

    Parameters
    ----------
    base_url : str, default="http://localhost:11434"
        Ollama server base URL.
    timeout : float, default=5.0
        Request timeout in seconds.

    Returns
    -------
    bool
        True if Ollama is accessible, False otherwise.

    Examples
    --------
    >>> if check_ollama_connection():
    ...     print("Ollama is running")
    """
    try:
        list_ollama_models(base_url, timeout)
        return True
    except ConnectionError:
        return False
