"""
Web fetch tool for retrieving web page content.

This module provides a tool for fetching content from URLs with
timeout support and content truncation.
"""

import logging
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


class WebFetchParams(BaseModel):
    """
    Parameters for the web_fetch tool.

    Parameters
    ----------
    url : str
        URL to fetch (must be http:// or https://).
    timeout : int, default=30
        Request timeout in seconds (5-120).

    Examples
    --------
    >>> params = WebFetchParams(url="https://example.com", timeout=30)
    """

    url: str = Field(..., description="URL to fetch (must be http:// or https://)")
    timeout: int = Field(
        30,
        ge=5,
        le=120,
        description="Request timeout in seconds (default: 30)",
    )


class WebFetchTool(Tool):
    """
    Tool for fetching content from URLs.

    This tool fetches web page content with timeout support and
    automatic content truncation for large responses.

    Attributes
    ----------
    name : str
        Tool name: "web_fetch"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: NETWORK
    schema : type[WebFetchParams]
        Parameter schema
    """

    name: str = "web_fetch"
    description: str = "Fetch content from a URL. Returns the response body as text"
    kind: ToolKind = ToolKind.NETWORK
    schema: type[WebFetchParams] = WebFetchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the web fetch.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters.

        Returns
        -------
        ToolResult
            Result containing fetched content or error message.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = WebFetchParams(**invocation.params)

        parsed = urlparse(params.url)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            return ToolResult.error_result("URL must be http:// or https://")

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(params.timeout),
                follow_redirects=True,
            ) as client:
                response = await client.get(params.url)
                response.raise_for_status()
                text: str = response.text
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP error {e.response.status_code} for {params.url}: {e.response.reason_phrase}",
            )
            return ToolResult.error_result(
                f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        except Exception as e:
            logger.exception(f"Request failed for {params.url}: {e}")
            return ToolResult.error_result(f"Request failed: {e}")

        if len(text) > 100 * 1024:
            text = text[: 100 * 1024] + "\n... [content truncated]"

        return ToolResult.success_result(
            text,
            metadata={
                "status_code": response.status_code,
                "content_length": len(response.content),
            },
        )
