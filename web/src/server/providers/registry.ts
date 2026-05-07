import { z } from "zod"
import { isChinaDestination } from "@/domain/geography"
import {
  NormalizedPlace,
  NormalizedPlaceSchema,
  NormalizedRoute,
  NormalizedRouteSchema,
} from "@/domain/schemas"
import { AMapMapProvider } from "./map/amap"
import { MapboxMapProvider } from "./map/mapbox"
import {
  GeocodeRequest,
  MapProvider,
  PlaceSearchRequest,
  ProviderAttemptFailure,
  ProviderError,
  ProviderFailureCode,
  ProviderHealth,
  ProviderId,
  ProviderKind,
  RouteRequest,
  ReverseGeocodeRequest,
  SearchProvider,
  SupplierProvider,
  WeatherProvider,
} from "./types"

const DEFAULT_OPERATION_TIMEOUT_MS = 8_000

export interface RegistryGeocodeRequest extends GeocodeRequest {
  countryCode: string
}

export interface RegistryPlaceSearchRequest extends PlaceSearchRequest {
  countryCode: string
}

export interface ProviderRegistryConfig {
  mapProviders: Partial<Record<ProviderId, MapProvider>>
  searchProvider?: SearchProvider
  weatherProvider?: WeatherProvider
  supplierProvider?: SupplierProvider
  operationTimeoutMs?: number
}

export class ProviderRegistryError extends Error {
  readonly code = "PROVIDER_FALLBACK_FAILED" as const
  readonly attempts: ProviderAttemptFailure[]

  constructor(operation: string, attempts: ProviderAttemptFailure[]) {
    super(`All configured providers failed for ${operation}`)
    this.name = "ProviderRegistryError"
    this.attempts = attempts
  }
}

export class TravelDataProviderRegistry {
  private readonly mapProviders: Partial<Record<ProviderId, MapProvider>>
  private readonly operationTimeoutMs: number

  constructor(config: ProviderRegistryConfig) {
    this.mapProviders = config.mapProviders
    this.operationTimeoutMs = config.operationTimeoutMs ?? DEFAULT_OPERATION_TIMEOUT_MS
  }

  async geocode(request: RegistryGeocodeRequest): Promise<NormalizedPlace> {
    return this.runMapOperation({
      countryCode: request.countryCode,
      operation: "geocode",
      execute: (provider) =>
        provider.geocode({
          query: request.query,
          countryCode: request.countryCode,
          bias: request.bias,
        }),
      validate: (value) => NormalizedPlaceSchema.parse(value),
    })
  }

  async reverseGeocode(
    countryCode: string,
    request: ReverseGeocodeRequest
  ): Promise<NormalizedPlace> {
    return this.runMapOperation({
      countryCode,
      operation: "reverseGeocode",
      execute: (provider) => provider.reverseGeocode(request),
      validate: (value) => NormalizedPlaceSchema.parse(value),
    })
  }

  async searchPlaces(request: RegistryPlaceSearchRequest): Promise<NormalizedPlace[]> {
    return this.runMapOperation({
      countryCode: request.countryCode,
      operation: "searchPlaces",
      execute: (provider) =>
        provider.searchPlaces({
          query: request.query,
          countryCode: request.countryCode,
          bias: request.bias,
          category: request.category,
          limit: request.limit,
        }),
      validate: (value) => NormalizedPlaceSchema.array().parse(value),
    })
  }

  async route(countryCode: string, request: RouteRequest): Promise<NormalizedRoute> {
    return this.runMapOperation({
      countryCode,
      operation: "route",
      execute: (provider) => provider.route(request),
      validate: (value) => NormalizedRouteSchema.parse(value),
    })
  }

  private async runMapOperation<T>(input: {
    countryCode: string
    operation: string
    execute: (provider: MapProvider) => Promise<unknown>
    validate: (value: unknown) => T
  }): Promise<T> {
    const attempts: ProviderAttemptFailure[] = []
    const providers = this.getMapProviderRunList(input.countryCode)

    for (const provider of providers) {
      const health = await this.checkHealth(provider, input.operation)
      if (!health.ok) {
        attempts.push({
          provider: provider.name,
          kind: "map",
          operation: input.operation,
          code: "unhealthy",
          message: health.reason ?? `${provider.name} is unhealthy`,
        })
        continue
      }

      try {
        const value = await this.withTimeout(
          () => input.execute(provider),
          provider.name,
          "map",
          input.operation
        )
        return input.validate(value)
      } catch (error) {
        attempts.push(toAttemptFailure(provider.name, "map", input.operation, error))
      }
    }

    throw new ProviderRegistryError(input.operation, attempts)
  }

  private getMapProviderRunList(countryCode: string): MapProvider[] {
    const providerOrder = getMapProviderOrder(countryCode)
    const [primaryId, ...fallbackIds] = providerOrder
    const providers: MapProvider[] = []
    const primary = this.mapProviders[primaryId]
    if (primary) providers.push(primary)

    const fallback = fallbackIds
      .map((providerId) => this.mapProviders[providerId])
      .find((provider): provider is MapProvider => Boolean(provider))
    if (fallback) providers.push(fallback)

    if (providers.length === 0) {
      const firstConfigured = Object.values(this.mapProviders)[0]
      if (firstConfigured) providers.push(firstConfigured)
    }

    return providers
  }

  private async checkHealth(provider: MapProvider, operation: string): Promise<ProviderHealth> {
    try {
      return await this.withTimeout(() => provider.health(), provider.name, "map", `${operation}:health`)
    } catch (error) {
      const failure = toAttemptFailure(provider.name, "map", `${operation}:health`, error)
      return { ok: false, reason: failure.message }
    }
  }

  private async withTimeout<T>(
    operation: () => Promise<T>,
    provider: ProviderId,
    kind: ProviderKind,
    operationName: string
  ): Promise<T> {
    let timeoutHandle: ReturnType<typeof setTimeout> | undefined
    const timeout = new Promise<never>((_, reject) => {
      timeoutHandle = setTimeout(() => {
        reject(
          new ProviderError({
            provider,
            kind,
            code: "timeout",
            message: `${provider} ${operationName} timed out after ${this.operationTimeoutMs}ms`,
          })
        )
      }, this.operationTimeoutMs)
    })

    try {
      return await Promise.race([operation(), timeout])
    } finally {
      if (timeoutHandle) clearTimeout(timeoutHandle)
    }
  }
}

export function createProviderRegistry(config: ProviderRegistryConfig): TravelDataProviderRegistry {
  return new TravelDataProviderRegistry(config)
}

export function createDefaultProviderRegistry(env: NodeJS.ProcessEnv = process.env) {
  return createProviderRegistry({
    mapProviders: {
      amap: new AMapMapProvider({ apiKey: env.AMAP_API_KEY }),
      mapbox: new MapboxMapProvider({ accessToken: env.MAPBOX_ACCESS_TOKEN }),
    },
  })
}

export function getMapProviderOrder(countryCode: string): ProviderId[] {
  return isChinaDestination(countryCode)
    ? ["amap", "baidu", "mapbox", "google"]
    : ["mapbox", "google", "amap", "baidu"]
}

function toAttemptFailure(
  provider: ProviderId,
  kind: ProviderKind,
  operation: string,
  error: unknown
): ProviderAttemptFailure {
  if (error instanceof ProviderError) {
    return {
      provider,
      kind,
      operation,
      code: error.code,
      message: error.message,
    }
  }

  if (error instanceof z.ZodError) {
    return {
      provider,
      kind,
      operation,
      code: "invalid_normalized_payload",
      message: error.message,
    }
  }

  return {
    provider,
    kind,
    operation,
    code: inferProviderFailureCode(error),
    message: error instanceof Error ? error.message : String(error),
  }
}

function inferProviderFailureCode(error: unknown): ProviderFailureCode {
  if (error instanceof TypeError) return "network_failure"
  return "unknown_failure"
}
