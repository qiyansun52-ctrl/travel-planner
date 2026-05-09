from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from app.providers.search.tavily import TavilySearchProvider, build_search_queries
from app.providers.types import ProviderError, SearchRequest
from app.services.tavily import search_tavily_three_sections


def test_build_search_queries_returns_three_chinese_queries() -> None:
    q1, q2, q3 = build_search_queries("上海")
    assert "上海" in q1 and "景点" in q1
    assert "上海" in q2 and "交通" in q2
    assert "上海" in q3 and "美食" in q3


async def test_tavily_health_reports_missing_key() -> None:
    provider = TavilySearchProvider(api_key=None)
    health = await provider.health()
    assert health.ok is False
    assert health.reason == "TAVILY_API_KEY is not configured"


async def test_tavily_search_normalizes_results(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.tavily.com/search",
        json={
            "results": [
                {
                    "title": "Shanghai guide",
                    "url": "https://example.com/shanghai",
                    "content": "Useful guide",
                }
            ]
        },
    )
    provider = TavilySearchProvider(api_key="key")
    results = await provider.search(
        SearchRequest(query="Shanghai guide", country_code="CN", limit=1)
    )
    assert len(results) == 1
    assert results[0].title == "Shanghai guide"
    assert results[0].url == "https://example.com/shanghai"
    assert results[0].snippet == "Useful guide"
    assert results[0].source_note is not None
    assert results[0].source_note.provider == "tavily"

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert payload["api_key"] == "key"
    assert payload["query"] == "Shanghai guide"
    assert payload["search_depth"] == "basic"
    assert payload["max_results"] == 1
    assert payload["include_answer"] is False


async def test_tavily_search_maps_401_to_auth_failure(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST", url="https://api.tavily.com/search", status_code=401, json={}
    )
    provider = TavilySearchProvider(api_key="bad")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "auth_failure"


async def test_tavily_search_maps_non_success_to_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST", url="https://api.tavily.com/search", status_code=302, json={}
    )
    provider = TavilySearchProvider(api_key="key")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "network_failure"


async def test_tavily_search_maps_malformed_json_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST", url="https://api.tavily.com/search", content=b"not json"
    )
    provider = TavilySearchProvider(api_key="key")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "invalid_normalized_payload"


async def test_tavily_search_maps_non_object_json_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(method="POST", url="https://api.tavily.com/search", json=[])
    provider = TavilySearchProvider(api_key="key")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "invalid_normalized_payload"


async def test_tavily_search_maps_invalid_results_shape_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.tavily.com/search",
        json={"results": {"bad": "shape"}},
    )
    provider = TavilySearchProvider(api_key="key")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "invalid_normalized_payload"


async def test_tavily_search_maps_invalid_result_item_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST", url="https://api.tavily.com/search", json={"results": [123]}
    )
    provider = TavilySearchProvider(api_key="key")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "invalid_normalized_payload"


async def test_tavily_search_maps_invalid_normalized_result_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.tavily.com/search",
        json={
            "results": [
                {
                    "title": [],
                    "url": "https://example.com",
                    "content": "snippet",
                }
            ]
        },
    )
    provider = TavilySearchProvider(api_key="key")
    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "invalid_normalized_payload"


async def test_legacy_three_section_shim_returns_search_items(
    httpx_mock: HTTPXMock,
) -> None:
    for title in ["A", "B", "C"]:
        httpx_mock.add_response(
            method="POST",
            url="https://api.tavily.com/search",
            json={
                "results": [
                    {
                        "title": title,
                        "url": f"https://example.com/{title}",
                        "content": "snippet",
                    }
                ]
            },
        )

    experience, transport, food = await search_tavily_three_sections("上海", "key")
    assert experience[0].title == "A"
    assert transport[0].title == "B"
    assert food[0].title == "C"


async def test_legacy_three_section_shim_swallows_failed_section(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST", url="https://api.tavily.com/search", status_code=500, json={}
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.tavily.com/search",
        json={
            "results": [
                {
                    "title": "B",
                    "url": "https://example.com/B",
                    "content": "snippet",
                }
            ]
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.tavily.com/search",
        json={
            "results": [
                {
                    "title": "C",
                    "url": "https://example.com/C",
                    "content": "snippet",
                }
            ]
        },
    )

    experience, transport, food = await search_tavily_three_sections("上海", "key")
    assert experience == []
    assert transport[0].title == "B"
    assert food[0].title == "C"
