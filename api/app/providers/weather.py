"""Weather provider fallback for MVP."""
from __future__ import annotations

from app.providers.types import ProviderError, ProviderHealth, WeatherRequest, WeatherSummary


class UnavailableWeatherProvider:
    name = "google"

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=False, reason="Weather provider is not configured")

    async def get_weather_summary(self, request: WeatherRequest) -> WeatherSummary:
        raise ProviderError(
            provider=self.name,
            kind="weather",
            code="capability_unavailable",
            message="Weather provider is not configured",
        )


def create_unavailable_weather_provider() -> UnavailableWeatherProvider:
    return UnavailableWeatherProvider()
