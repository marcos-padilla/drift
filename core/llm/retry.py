"""
Retry strategy for LLM API calls.

This module provides retry logic with exponential backoff for handling
transient failures in LLM API requests.
"""

import asyncio
import logging
from typing import Any, Callable, TypeVar

from openai import APIConnectionError, APIError, RateLimitError as OpenAIRateLimitError

from core.constants import DEFAULT_RETRY_BASE_DELAY, DEFAULT_RETRY_MAX_DELAY
from core.exceptions import ConnectionError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy:
    """
    Strategy for retrying failed operations with exponential backoff.

    Parameters
    ----------
    max_retries : int, default=3
        Maximum number of retry attempts.
    base_delay : float, default=1.0
        Base delay in seconds for exponential backoff.
    max_delay : float, default=60.0
        Maximum delay in seconds between retries.

    Examples
    --------
    >>> strategy = RetryStrategy(max_retries=3, base_delay=1.0)
    >>> result = await strategy.execute(some_async_function)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    ) -> None:
        self.max_retries: int = max_retries
        self.base_delay: float = base_delay
        self.max_delay: float = max_delay

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt using exponential backoff.

        Parameters
        ----------
        attempt : int
            The attempt number (0-indexed).

        Returns
        -------
        float
            Delay in seconds.
        """
        delay: float = self.base_delay * (2**attempt)
        return min(delay, self.max_delay)

    async def execute(
        self,
        func: Callable[[], Any],
        *,
        on_retry: Callable[[Exception, int], None] | None = None,
    ) -> Any:
        """
        Execute a function with retry logic.

        Parameters
        ----------
        func : Callable[[], Any]
            Async function to execute.
        on_retry : Callable[[Exception, int], None] | None, optional
            Callback called before each retry with the exception and attempt number.

        Returns
        -------
        Any
            Result of the function execution.

        Raises
        ------
        Exception
            The last exception if all retries are exhausted, or a non-retryable error.
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func()
            except OpenAIRateLimitError as e:
                if attempt < self.max_retries:
                    wait_time: float = self._calculate_delay(attempt)
                    logger.warning(
                        f"Rate limit exceeded (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time:.2f}s",
                    )
                    if on_retry:
                        on_retry(e, attempt)
                    await asyncio.sleep(wait_time)
                    last_exception = e
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries: {e}",
                        retry_after=wait_time if attempt > 0 else None,
                        cause=e,
                    ) from e
            except APIConnectionError as e:
                if attempt < self.max_retries:
                    wait_time = self._calculate_delay(attempt)
                    logger.warning(
                        f"Connection error (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time:.2f}s: {e}",
                    )
                    if on_retry:
                        on_retry(e, attempt)
                    await asyncio.sleep(wait_time)
                    last_exception = e
                else:
                    raise ConnectionError(
                        f"Connection failed after {self.max_retries} retries: {e}",
                        cause=e,
                    ) from e
            except APIError as e:
                # API errors are typically not retryable
                logger.error(f"API error: {e}")
                raise e
            except Exception as e:
                # Other exceptions are not retryable
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise e

        # Should never reach here, but type checker needs it
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry strategy exhausted without result")
