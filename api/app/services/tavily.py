"""Async Tavily search client.

Python port of `web/src/lib/googleSearch.ts` (which actually uses Tavily despite
the file name — a holdover from the Google CSE migration).
"""

import asyncio

import httpx

from app.prompts.discover import SearchItem


def build_search_queries(destination: str) -> tuple[str, str, str]:
    """Build the three section-specific queries used by /api/discover."""
    return (
        f"{destination} 必去景点 旅游体验 攻略 2025",
        f"{destination} 交通攻略 怎么去 市内出行 交通方式",
        f"{destination} 美食推荐 必吃 餐厅 小吃 2025",
    )


def _parse_results(results: list[dict]) -> list[SearchItem]:
    """Normalize Tavily results into our SearchItem shape."""
    return [
        SearchItem(
            title=r.get("title", "") or "",
            snippet=r.get("content", "") or "",
            link=r.get("url", "") or "",
            imageUrl="",
        )
        for r in results
    ]


async def search_tavily(query: str, api_key: str) -> list[SearchItem]:
    """Fire a single Tavily search and return normalized results."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 8,
                "include_answer": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return _parse_results(data.get("results", []))


async def search_tavily_three_sections(
    destination: str, api_key: str
) -> tuple[list[SearchItem], list[SearchItem], list[SearchItem]]:
    """Run the three section-specific searches in parallel.

    Returns (experience_items, transport_items, food_items). Failed queries
    return empty lists so the caller can continue (Gemini still has fallback knowledge).
    """
    q1, q2, q3 = build_search_queries(destination)
    results = await asyncio.gather(
        search_tavily(q1, api_key),
        search_tavily(q2, api_key),
        search_tavily(q3, api_key),
        return_exceptions=True,
    )

    def safe(r) -> list[SearchItem]:
        return r if isinstance(r, list) else []

    return safe(results[0]), safe(results[1]), safe(results[2])
