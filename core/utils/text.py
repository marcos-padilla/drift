"""
Text processing utilities for token counting and truncation.

This module provides functionality for counting tokens in text and truncating
text to fit within token limits, with support for different models and
tokenization strategies.
"""

import logging
from typing import Callable

import tiktoken

from core.constants import (
    DEFAULT_CHARS_PER_TOKEN,
    DEFAULT_ENCODING,
    MIN_TOKEN_COUNT,
)

logger = logging.getLogger(__name__)


class Tokenizer:
    """
    Tokenizer for counting and processing tokens in text.

    This class provides token counting and text truncation capabilities
    with caching for improved performance.

    Parameters
    ----------
    model : str, default="gpt-4o"
        Model name to use for tokenization.

    Attributes
    ----------
    model : str
        Model name.
    _encoder : Callable[[str], list[int]] | None
        Cached encoder function.

    Examples
    --------
    >>> tokenizer = Tokenizer(model="gpt-4o")
    >>> count = tokenizer.count_tokens("Hello, world!")
    >>> truncated = tokenizer.truncate("Very long text...", max_tokens=100)
    """

    def __init__(self, model: str = "gpt-4o") -> None:
        self.model: str = model
        self._encoder: Callable[[str], list[int]] | None = None

    def _get_encoder(self) -> Callable[[str], list[int]]:
        """
        Get or create the tokenizer encoder function.

        Returns
        -------
        Callable[[str], list[int]]
            Encoder function that takes text and returns token IDs.
        """
        if self._encoder is None:
            try:
                encoding = tiktoken.encoding_for_model(self.model)
                self._encoder = encoding.encode
                logger.debug(f"Initialized tokenizer for model: {self.model}")
            except Exception as e:
                logger.warning(
                    f"Failed to get encoding for model {self.model}, "
                    f"falling back to cl100k_base: {e}",
                )
                encoding = tiktoken.get_encoding("cl100k_base")
                self._encoder = encoding.encode

        return self._encoder

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.

        Parameters
        ----------
        text : str
            The text to count tokens for.

        Returns
        -------
        int
            The number of tokens in the text.

        Examples
        --------
        >>> tokenizer = Tokenizer()
        >>> count = tokenizer.count_tokens("Hello, world!")
        >>> print(count)
        3
        """
        if not text:
            return 0

        encoder = self._get_encoder()
        try:
            return len(encoder(text))
        except Exception as e:
            logger.warning(f"Token counting failed, using estimation: {e}")
            return self._estimate_tokens(text)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using character-based approximation.

        Parameters
        ----------
        text : str
            The text to estimate tokens for.

        Returns
        -------
        int
            Estimated token count.
        """
        return max(MIN_TOKEN_COUNT, len(text) // DEFAULT_CHARS_PER_TOKEN)

    def truncate(
        self,
        text: str,
        max_tokens: int,
        suffix: str = "\n... [truncated]",
        preserve_lines: bool = True,
    ) -> str:
        """
        Truncate text to fit within a token limit.

        Parameters
        ----------
        text : str
            The text to truncate.
        max_tokens : int
            Maximum number of tokens allowed.
        suffix : str, default="\\n... [truncated]"
            Suffix to append when text is truncated.
        preserve_lines : bool, default=True
            Whether to preserve complete lines when truncating.

        Returns
        -------
        str
            The truncated text (or original if within limit).

        Examples
        --------
        >>> tokenizer = Tokenizer()
        >>> long_text = "A" * 1000
        >>> truncated = tokenizer.truncate(long_text, max_tokens=100)
        """
        current_tokens: int = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text

        suffix_tokens: int = self.count_tokens(suffix)
        target_tokens: int = max_tokens - suffix_tokens

        if target_tokens <= 0:
            return suffix.strip()

        if preserve_lines:
            return self._truncate_by_lines(text, target_tokens, suffix)
        else:
            return self._truncate_by_chars(text, target_tokens, suffix)

    def _truncate_by_lines(
        self,
        text: str,
        target_tokens: int,
        suffix: str,
    ) -> str:
        """
        Truncate text preserving complete lines.

        Parameters
        ----------
        text : str
            The text to truncate.
        target_tokens : int
            Target number of tokens.
        suffix : str
            Suffix to append.

        Returns
        -------
        str
            Truncated text with complete lines.
        """
        lines: list[str] = text.split("\n")
        result_lines: list[str] = []
        current_tokens: int = 0

        for line in lines:
            line_with_newline: str = line + "\n"
            line_tokens: int = self.count_tokens(line_with_newline)
            if current_tokens + line_tokens > target_tokens:
                break
            result_lines.append(line)
            current_tokens += line_tokens

        if not result_lines:
            # Fall back to character truncation if no complete lines fit
            return self._truncate_by_chars(text, target_tokens, suffix)

        return "\n".join(result_lines) + suffix

    def _truncate_by_chars(
        self,
        text: str,
        target_tokens: int,
        suffix: str,
    ) -> str:
        """
        Truncate text by characters using binary search.

        Parameters
        ----------
        text : str
            The text to truncate.
        target_tokens : int
            Target number of tokens.
        suffix : str
            Suffix to append.

        Returns
        -------
        str
            Truncated text.
        """
        # Binary search for the right length
        low: int = 0
        high: int = len(text)

        while low < high:
            mid: int = (low + high + 1) // 2
            if self.count_tokens(text[:mid]) <= target_tokens:
                low = mid
            else:
                high = mid - 1

        return text[:low] + suffix


def get_tokenizer(model: str = "gpt-4o") -> Tokenizer:
    """
    Get a Tokenizer instance for the specified model.

    Parameters
    ----------
    model : str, default="gpt-4o"
        Model name to use for tokenization.

    Returns
    -------
    Tokenizer
        Tokenizer instance.

    Examples
    --------
    >>> tokenizer = get_tokenizer("gpt-4o")
    >>> count = tokenizer.count_tokens("Hello")
    """
    return Tokenizer(model=model)


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Count tokens in text for the specified model.

    Parameters
    ----------
    text : str
        The text to count tokens for.
    model : str, default="gpt-4o"
        Model name to use for tokenization.

    Returns
    -------
    int
        Number of tokens.

    Examples
    --------
    >>> count = count_tokens("Hello, world!", model="gpt-4o")
    """
    tokenizer = Tokenizer(model=model)
    return tokenizer.count_tokens(text)


def truncate_text(
    text: str,
    model: str,
    max_tokens: int,
    suffix: str = "\n... [truncated]",
    preserve_lines: bool = True,
) -> str:
    """
    Truncate text to fit within a token limit.

    Parameters
    ----------
    text : str
        The text to truncate.
    model : str
        Model name to use for tokenization.
    max_tokens : int
        Maximum number of tokens allowed.
    suffix : str, default="\\n... [truncated]"
        Suffix to append when text is truncated.
    preserve_lines : bool, default=True
        Whether to preserve complete lines when truncating.

    Returns
    -------
    str
        The truncated text.

    Examples
    --------
    >>> truncated = truncate_text("Very long text...", "gpt-4o", max_tokens=100)
    """
    tokenizer = Tokenizer(model=model)
    return tokenizer.truncate(text, max_tokens, suffix, preserve_lines)
