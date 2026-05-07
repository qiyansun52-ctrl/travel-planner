import {
  ProviderError,
  SearchProvider,
  SearchResult,
} from "../types"

export class UnavailableSearchProvider implements SearchProvider {
  readonly name = "google" as const

  async health() {
    return { ok: false, reason: "Search provider is not configured" }
  }

  async search(): Promise<SearchResult[]> {
    throw new ProviderError({
      provider: this.name,
      kind: "search",
      code: "capability_unavailable",
      message: "Search provider is not configured",
    })
  }
}

export function createUnavailableSearchProvider(): SearchProvider {
  return new UnavailableSearchProvider()
}
