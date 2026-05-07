import {
  NormalizedPlace,
  NormalizedPlaceSchema,
  NormalizedRoute,
  NormalizedRouteSchema,
} from "@/domain/schemas"
import {
  GeocodeRequest,
  MapProvider,
  PlaceSearchRequest,
  ProviderError,
  RouteRequest,
} from "../types"

type Fetcher = typeof fetch

export interface MapboxMapProviderOptions {
  accessToken?: string
  fetcher?: Fetcher
}

interface MapboxFeature {
  id?: string
  type?: string
  text?: string
  place_name?: string
  geometry?: {
    coordinates?: [number, number]
  }
  properties?: {
    name?: string
    full_address?: string
    feature_type?: string
  }
}

interface MapboxGeocodeResponse {
  features?: MapboxFeature[]
}

interface MapboxDirectionsResponse {
  routes?: Array<{
    duration?: number
    distance?: number
  }>
}

export class MapboxMapProvider implements MapProvider {
  readonly name = "mapbox" as const
  private readonly accessToken: string | undefined
  private readonly fetcher: Fetcher

  constructor(options: MapboxMapProviderOptions = {}) {
    this.accessToken = options.accessToken
    this.fetcher = options.fetcher ?? fetch
  }

  async health() {
    if (!this.accessToken) {
      return { ok: false, reason: "MAPBOX_ACCESS_TOKEN is not configured" }
    }

    return { ok: true }
  }

  async geocode(request: GeocodeRequest): Promise<NormalizedPlace> {
    const features = await this.fetchForwardGeocode(request, request.countryCode, 1)
    const first = features[0]
    if (!first) {
      throw this.providerError("unknown_failure", "Mapbox geocode returned no place")
    }

    return normalizeMapboxFeature(first)
  }

  async reverseGeocode(request: { coordinate: { lat: number; lng: number } }): Promise<NormalizedPlace> {
    const accessToken = this.requireAccessToken()
    const url = new URL(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${request.coordinate.lng},${request.coordinate.lat}.json`
    )
    url.searchParams.set("access_token", accessToken)
    url.searchParams.set("limit", "1")

    const body = await this.fetchJson<MapboxGeocodeResponse>(url, "reverseGeocode")
    const first = body.features?.[0]
    if (!first) {
      throw this.providerError("unknown_failure", "Mapbox reverse geocode returned no place")
    }

    return normalizeMapboxFeature(first)
  }

  async searchPlaces(request: PlaceSearchRequest): Promise<NormalizedPlace[]> {
    const features = await this.fetchForwardGeocode(request, request.countryCode, request.limit ?? 10)
    return features.map(normalizeMapboxFeature)
  }

  async route(request: RouteRequest): Promise<NormalizedRoute> {
    const accessToken = this.requireAccessToken()
    if (!request.from.coordinate || !request.to.coordinate) {
      throw this.providerError("invalid_normalized_payload", "Mapbox route requires coordinates")
    }

    const profile = toMapboxDirectionsProfile(request.mode)
    const coordinates = `${request.from.coordinate.lng},${request.from.coordinate.lat};${request.to.coordinate.lng},${request.to.coordinate.lat}`
    const url = new URL(`https://api.mapbox.com/directions/v5/mapbox/${profile}/${coordinates}`)
    url.searchParams.set("access_token", accessToken)
    url.searchParams.set("overview", "false")

    const body = await this.fetchJson<MapboxDirectionsResponse>(url, "route")
    const first = body.routes?.[0]
    if (!first || typeof first.duration !== "number" || typeof first.distance !== "number") {
      throw this.providerError("unknown_failure", "Mapbox route returned no route")
    }

    return NormalizedRouteSchema.parse({
      from: request.from,
      to: request.to,
      mode: request.mode,
      duration_minutes: Math.round(first.duration / 60),
      distance_meters: first.distance,
      cost_estimate: null,
      provider: "mapbox",
    })
  }

  private async fetchForwardGeocode(
    request: GeocodeRequest,
    countryCode: string | undefined,
    limit: number
  ): Promise<MapboxFeature[]> {
    const accessToken = this.requireAccessToken()
    const url = new URL("https://api.mapbox.com/geocoding/v5/mapbox.places/forward.json")
    url.pathname = `/geocoding/v5/mapbox.places/${encodeURIComponent(request.query)}.json`
    url.searchParams.set("access_token", accessToken)
    url.searchParams.set("limit", String(limit))
    if (countryCode) url.searchParams.set("country", countryCode)
    if (request.bias) {
      url.searchParams.set("proximity", `${request.bias.lng},${request.bias.lat}`)
    }

    const body = await this.fetchJson<MapboxGeocodeResponse>(url, "geocode")
    return body.features ?? []
  }

  private async fetchJson<T>(url: URL, operation: string): Promise<T> {
    let response: Response
    try {
      response = await this.fetcher(url)
    } catch (error) {
      throw this.providerError("network_failure", `Mapbox ${operation} network failure`, error)
    }

    if (response.status === 401 || response.status === 403) {
      throw this.providerError("auth_failure", `Mapbox ${operation} auth failure`)
    }

    if (!response.ok) {
      throw this.providerError("network_failure", `Mapbox ${operation} HTTP ${response.status}`)
    }

    return response.json() as Promise<T>
  }

  private requireAccessToken(): string {
    if (!this.accessToken) {
      throw this.providerError("auth_failure", "MAPBOX_ACCESS_TOKEN is not configured")
    }

    return this.accessToken
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

export function normalizeMapboxFeature(feature: MapboxFeature): NormalizedPlace {
  const [lng, lat] = feature.geometry?.coordinates ?? []
  const name = feature.properties?.name ?? feature.text ?? feature.place_name

  return NormalizedPlaceSchema.parse({
    id: `mapbox:${feature.id ?? encodeURIComponent(`${name ?? "place"}:${lng},${lat}`)}`,
    name,
    coordinate: Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null,
    address: feature.properties?.full_address ?? feature.place_name ?? null,
    category: feature.properties?.feature_type ?? feature.type ?? null,
    provider: "mapbox",
  })
}

function toMapboxDirectionsProfile(mode: NormalizedRoute["mode"]): "walking" | "driving" {
  if (mode === "walk") return "walking"
  if (mode === "drive") return "driving"

  throw new ProviderError({
    provider: "mapbox",
    kind: "map",
    code: "capability_unavailable",
    message: `Mapbox routing does not support ${mode} routes in this adapter`,
  })
}
