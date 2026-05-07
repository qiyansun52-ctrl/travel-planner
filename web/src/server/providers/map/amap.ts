import { NormalizedPlace, NormalizedPlaceSchema, NormalizedRoute } from "@/domain/schemas"
import { GeocodeRequest, MapProvider, PlaceSearchRequest, ProviderError } from "../types"
import { convertGcj02ToWgs84 } from "./coordinateConversion"

type Fetcher = typeof fetch

export interface AMapMapProviderOptions {
  apiKey?: string
  fetcher?: Fetcher
}

export interface AMapPlacePayload {
  id?: string
  name?: string
  formatted_address?: string
  address?: string
  category?: string
  type?: string
  location: string
}

interface AMapGeocodeResponse {
  status?: string
  info?: string
  geocodes?: Array<{
    adcode?: string
    formatted_address?: string
    location?: string
    level?: string
  }>
}

interface AMapPlaceSearchResponse {
  status?: string
  info?: string
  pois?: AMapPlacePayload[]
}

export class AMapMapProvider implements MapProvider {
  readonly name = "amap" as const
  private readonly apiKey: string | undefined
  private readonly fetcher: Fetcher

  constructor(options: AMapMapProviderOptions = {}) {
    this.apiKey = options.apiKey
    this.fetcher = options.fetcher ?? fetch
  }

  async health() {
    if (!this.apiKey) {
      return { ok: false, reason: "AMAP_API_KEY is not configured" }
    }

    return { ok: true }
  }

  async geocode(request: GeocodeRequest): Promise<NormalizedPlace> {
    const apiKey = this.requireApiKey()
    const url = new URL("https://restapi.amap.com/v3/geocode/geo")
    url.searchParams.set("key", apiKey)
    url.searchParams.set("address", request.query)

    const body = await this.fetchJson<AMapGeocodeResponse>(url, "geocode")
    if (body.status !== "1") {
      throw this.providerError("unknown_failure", body.info ?? "AMap geocode failed")
    }

    const first = body.geocodes?.[0]
    if (!first?.location) {
      throw this.providerError("unknown_failure", "AMap geocode returned no place")
    }

    return normalizeAMapPlace({
      id: first.adcode,
      name: request.query,
      formatted_address: first.formatted_address,
      category: first.level,
      location: first.location,
    })
  }

  async reverseGeocode(): Promise<NormalizedPlace> {
    throw this.providerError("capability_unavailable", "AMap reverse geocoding is not wired yet")
  }

  async searchPlaces(request: PlaceSearchRequest): Promise<NormalizedPlace[]> {
    const apiKey = this.requireApiKey()
    const url = new URL("https://restapi.amap.com/v3/place/text")
    url.searchParams.set("key", apiKey)
    url.searchParams.set("keywords", request.query)
    url.searchParams.set("offset", String(request.limit ?? 10))

    const body = await this.fetchJson<AMapPlaceSearchResponse>(url, "searchPlaces")
    if (body.status !== "1") {
      throw this.providerError("unknown_failure", body.info ?? "AMap place search failed")
    }

    return (body.pois ?? []).map(normalizeAMapPlace)
  }

  async route(): Promise<NormalizedRoute> {
    throw this.providerError("capability_unavailable", "AMap routing is not wired yet")
  }

  private async fetchJson<T>(url: URL, operation: string): Promise<T> {
    let response: Response
    try {
      response = await this.fetcher(url)
    } catch (error) {
      throw this.providerError("network_failure", `AMap ${operation} network failure`, error)
    }

    if (response.status === 401 || response.status === 403) {
      throw this.providerError("auth_failure", `AMap ${operation} auth failure`)
    }

    if (!response.ok) {
      throw this.providerError("network_failure", `AMap ${operation} HTTP ${response.status}`)
    }

    return response.json() as Promise<T>
  }

  private requireApiKey(): string {
    if (!this.apiKey) {
      throw this.providerError("auth_failure", "AMAP_API_KEY is not configured")
    }

    return this.apiKey
  }

  private providerError(
    code: ProviderError["code"],
    message: string,
    cause?: unknown
  ): ProviderError {
    return new ProviderError({
      provider: this.name,
      kind: "map",
      code,
      message,
      cause,
    })
  }
}

export function normalizeAMapPlace(payload: AMapPlacePayload): NormalizedPlace {
  const gcj02 = parseAMapLocation(payload.location)
  const coordinate = convertGcj02ToWgs84(gcj02)

  return NormalizedPlaceSchema.parse({
    id: `amap:${payload.id ?? createStableAmapId(payload)}`,
    name: payload.name ?? payload.formatted_address ?? payload.address ?? "AMap place",
    coordinate,
    address: payload.formatted_address ?? payload.address ?? null,
    category: payload.category ?? payload.type ?? null,
    provider: "amap",
  })
}

function parseAMapLocation(location: string) {
  const [lng, lat] = location.split(",").map(Number)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    throw new ProviderError({
      provider: "amap",
      kind: "map",
      code: "invalid_normalized_payload",
      message: `Invalid AMap location: ${location}`,
    })
  }

  return { lat, lng }
}

function createStableAmapId(payload: AMapPlacePayload): string {
  return encodeURIComponent(`${payload.name ?? payload.formatted_address ?? "place"}:${payload.location}`)
}
