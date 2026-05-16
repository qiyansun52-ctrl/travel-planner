"""Legacy Tavily helpers backed by the search provider adapter."""
from __future__ import annotations

import asyncio

from app.prompts.discover import SearchItem
from app.providers.search.tavily import TavilySearchProvider, build_search_queries
from app.providers.types import SearchResult, SearchRequest


def _to_search_item(result: SearchResult) -> SearchItem:
    return SearchItem(
        title=result.title,
        snippet=result.snippet,
        link=result.url or "",
        imageUrl="",
    )


async def search_tavily(query: str, api_key: str) -> list[SearchItem]:
    """Fire a single Tavily search and return legacy SearchItem objects."""
    provider = TavilySearchProvider(api_key=api_key)
    results = await provider.search(SearchRequest(query=query))
    return [_to_search_item(result) for result in results]


async def search_tavily_three_sections(
    destination: str, api_key: str
) -> tuple[list[SearchItem], list[SearchItem], list[SearchItem]]:
    """Run the three legacy section searches, swallowing failed sections."""
    q1, q2, q3 = build_search_queries(destination)
    results = await asyncio.gather(
        search_tavily(q1, api_key),
        search_tavily(q2, api_key),
        search_tavily(q3, api_key),
        return_exceptions=True,
    )

    def safe(result: object) -> list[SearchItem]:
        return result if isinstance(result, list) else []

    return safe(results[0]), safe(results[1]), safe(results[2])
