import type {
  BudgetBand,
  Coordinate,
  NormalizedPlace,
  NormalizedRoute,
  SourceNote,
} from "@/domain/schemas"

export type ProviderId = NormalizedPlace["provider"]
export type ProviderKind = "search" | "map" | "weather" | "supplier"

export type ProviderFailureCode =
  | "timeout"
  | "network_failure"
  | "auth_failure"
  | "unhealthy"
  | "invalid_normalized_payload"
  | "capability_unavailable"
  | "unknown_failure"

export interface ProviderHealth {
  ok: boolean
  reason?: string
}

export interface ProviderAttemptFailure {
  provider: ProviderId
  kind: ProviderKind
  operation: string
  code: ProviderFailureCode
  message: string
}

export class ProviderError extends Error {
  readonly code: ProviderFailureCode
  readonly provider: ProviderId
  readonly kind: ProviderKind
  readonly cause: unknown

  constructor(input: {
    provider: ProviderId
    kind: ProviderKind
    code: ProviderFailureCode
    message: string
    cause?: unknown
  }) {
    super(input.message)
    this.name = "ProviderError"
    this.provider = input.provider
    this.kind = input.kind
    this.code = input.code
    this.cause = input.cause
  }
}

export interface GeocodeRequest {
  query: string
  countryCode?: string
  bias?: Coordinate
}

export interface ReverseGeocodeRequest {
  coordinate: Coordinate
}

export interface PlaceSearchRequest extends GeocodeRequest {
  limit?: number
  category?: string
}

export interface RouteRequest {
  from: NormalizedPlace
  to: NormalizedPlace
  mode: NormalizedRoute["mode"]
}

export interface SearchRequest {
  query: string
  countryCode?: string
  limit?: number
}

export interface SearchResult {
  title: string
  url: string | null
  snippet: string
  source_note: SourceNote | null
}

export interface WeatherRequest {
  place: NormalizedPlace
  startDate: string
  durationDays: number
}

export interface WeatherSummary {
  provider: ProviderId
  place: NormalizedPlace
  summary: string
  daily_notes: string[]
  source_note: SourceNote | null
}

export interface SupplierRequest {
  destination: NormalizedPlace
  startDate: string
  durationDays: number
  currency: string
}

export interface SupplierReference {
  name: string
  category: "hotel" | "transport" | "activity"
  price_band: BudgetBand | null
  note: string
  source_note: SourceNote | null
}

export interface SearchProvider {
  readonly name: ProviderId
  health(): Promise<ProviderHealth>
  search(request: SearchRequest): Promise<SearchResult[]>
}

export interface MapProvider {
  readonly name: ProviderId
  health(): Promise<ProviderHealth>
  geocode(request: GeocodeRequest): Promise<NormalizedPlace>
  reverseGeocode(request: ReverseGeocodeRequest): Promise<NormalizedPlace>
  searchPlaces(request: PlaceSearchRequest): Promise<NormalizedPlace[]>
  route(request: RouteRequest): Promise<NormalizedRoute>
}

export interface WeatherProvider {
  readonly name: ProviderId
  health(): Promise<ProviderHealth>
  getWeatherSummary(request: WeatherRequest): Promise<WeatherSummary>
}

export interface SupplierProvider {
  readonly name: ProviderId
  health(): Promise<ProviderHealth>
  getSampleReferences(request: SupplierRequest): Promise<SupplierReference[]>
}
