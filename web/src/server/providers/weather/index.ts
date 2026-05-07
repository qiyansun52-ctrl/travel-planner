import {
  ProviderError,
  WeatherProvider,
  WeatherSummary,
} from "../types"

export class UnavailableWeatherProvider implements WeatherProvider {
  readonly name = "google" as const

  async health() {
    return { ok: false, reason: "Weather provider is not configured" }
  }

  async getWeatherSummary(): Promise<WeatherSummary> {
    throw new ProviderError({
      provider: this.name,
      kind: "weather",
      code: "capability_unavailable",
      message: "Weather provider is not configured",
    })
  }
}

export function createUnavailableWeatherProvider(): WeatherProvider {
  return new UnavailableWeatherProvider()
}
