"""Tavily search provider adapter."""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from app.models.schemas import SourceNote
from app.providers.types import (
    ProviderError,
    ProviderFailureCode,
    ProviderHealth,
    SearchRequest,
    SearchResult,
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def build_search_queries(destination: str) -> tuple[str, str, str]:
    """Build the three section-specific queries used by /api/discover."""
    return (
        f"{destination} 必去景点 旅游体验 攻略 2025",
        f"{destination} 交通攻略 怎么去 市内出行 交通方式",
        f"{destination} 美食推荐 必吃 餐厅 小吃 2025",
    )


class TavilySearchProvider:
    name = "tavily"

    def __init__(self, *, api_key: str | None = None) -> None:
        self._api_key = api_key

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(
                ok=False, reason="TAVILY_API_KEY is not configured"
            )
        return ProviderHealth(ok=True)

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        api_key = self._require_api_key()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    TAVILY_SEARCH_URL,
                    json={
                        "api_key": api_key,
                        "query": request.query,
                        "search_depth": "basic",
                        "max_results": request.limit or 8,
                        "include_answer": False,
                    },
                )
        except httpx.HTTPError as exc:
            raise self._provider_error(
                "network_failure", "Tavily search network failure", exc
            ) from exc

        if response.status_code in (401, 403):
            raise self._provider_error("auth_failure", "Tavily search auth failure")
        if not response.is_success:
            raise self._provider_error(
                "network_failure", f"Tavily search HTTP {response.status_code}"
            )

        body = _decode_tavily_json(response)
        if "results" not in body:
            raise _invalid_payload_error("Tavily results is missing")
        results = _expect_list(body["results"], "Tavily results")
        normalized: list[SearchResult] = []
        for result in results:
            if not isinstance(result, dict):
                raise _invalid_payload_error("Tavily search returned invalid result")
            normalized.append(_normalize_tavily_result(result))
        return normalized

    def _require_api_key(self) -> str:
        if not self._api_key:
            raise self._provider_error(
                "auth_failure", "TAVILY_API_KEY is not configured"
            )
        return self._api_key

    def _provider_error(
        self,
        code: ProviderFailureCode,
        message: str,
        cause: object | None = None,
    ) -> ProviderError:
        return ProviderError(
            provider=self.name,
            kind="search",
            code=code,
            message=message,
            cause=cause,
        )


def _decode_tavily_json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise _invalid_payload_error("Tavily search returned malformed JSON", exc) from exc

    if not isinstance(body, dict):
        raise _invalid_payload_error("Tavily search returned non-object JSON")
    return body


def _expect_list(value: object, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise _invalid_payload_error(f"{label} is invalid")
    return value


def _normalize_tavily_result(result: dict[str, Any]) -> SearchResult:
    title = _result_value(result, "title", "")
    url = _result_value(result, "url", None)
    snippet = _result_value(result, "content", "")
    try:
        source_note = (
            SourceNote(provider="tavily", url=url, note="Tavily search result")
            if url is not None
            else None
        )
        return SearchResult(
            title=title,
            url=url,
            snippet=snippet,
            source_note=source_note,
        )
    except ValidationError as exc:
        raise _invalid_payload_error(
            "Invalid Tavily normalized search result", exc
        ) from exc


def _result_value(
    result: dict[str, Any], key: str, default: str | None
) -> Any:
    value = result.get(key)
    return default if value is None else value


def _invalid_payload_error(
    message: str, cause: object | None = None
) -> ProviderError:
    return ProviderError(
        provider="tavily",
        kind="search",
        code="invalid_normalized_payload",
        message=message,
        cause=cause,
    )
