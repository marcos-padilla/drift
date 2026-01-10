"""
Web search tool for searching the internet.

This module provides a tool for searching the web using DuckDuckGo
and returning formatted search results.
"""

import logging
from typing import Any

from ddgs import DDGS
from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


class WebSearchParams(BaseModel):
    """
    Parameters for the web_search tool.

    Parameters
    ----------
    query : str
        Search query.
    max_results : int, default=10
        Maximum results to return (1-20).

    Examples
    --------
    >>> params = WebSearchParams(query="Python async programming", max_results=5)
    """

    query: str = Field(..., description="Search query")
    max_results: int = Field(
        10,
        ge=1,
        le=20,
        description="Maximum results to return (default: 10)",
    )


class WebSearchTool(Tool):
    """
    Tool for searching the web.

    This tool performs web searches using DuckDuckGo and returns
    formatted results with titles, URLs, and snippets.

    Attributes
    ----------
    name : str
        Tool name: "web_search"
    description : str
        Tool description
    kind : ToolKind
        Tool kind: NETWORK
    schema : type[WebSearchParams]
        Parameter schema
    """

    name: str = "web_search"
    description: str = (
        "Search the web for information. "
        "Returns search results with titles, URLs and snippets"
    )
    kind: ToolKind = ToolKind.NETWORK
    schema: type[WebSearchParams] = WebSearchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the web search.

        Parameters
        ----------
        invocation : ToolInvocation
            Tool invocation with parameters.

        Returns
        -------
        ToolResult
            Result containing formatted search results.

        Examples
        --------
        >>> result = await tool.execute(invocation)
        >>> if result.success:
        ...     print(result.output)
        """
        params = WebSearchParams(**invocation.params)

        try:
            results: list[dict[str, Any]] = list(
                DDGS().text(
                    params.query,
                    region="us-en",
                    safesearch="off",
                    timelimit="y",
                    page=1,
                    backend="auto",
                ),
            )
        except Exception as e:
            logger.exception(f"Web search failed for query '{params.query}': {e}")
            return ToolResult.error_result(f"Search failed: {e}")

        if not results:
            return ToolResult.success_result(
                f"No results found for: {params.query}",
                metadata={
                    "results": 0,
                },
            )

        # Limit results
        results = results[: params.max_results]

        output_lines: list[str] = [f"Search results for: {params.query}"]

        for i, result in enumerate(results, start=1):
            output_lines.append(f"{i}. Title: {result['title']}")
            output_lines.append(f"   URL: {result['href']}")
            if result.get("body"):
                output_lines.append(f"   Snippet: {result['body']}")

            output_lines.append("")

        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "results": len(results),
            },
        )
