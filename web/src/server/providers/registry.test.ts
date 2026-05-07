// @vitest-environment node

import { describe, expect, it } from "vitest"
import { NormalizedPlace } from "@/domain/schemas"
import { createProviderRegistry, ProviderRegistryError } from "./registry"
import { MapProvider } from "./types"

const amapPlace: NormalizedPlace = {
  id: "amap:shanghai",
  name: "Shanghai",
  coordinate: { lat: 31.2304, lng: 121.4737 },
  address: "Shanghai",
  category: "city",
  provider: "amap",
}

const mapboxPlace: NormalizedPlace = {
  id: "mapbox:shanghai",
  name: "Shanghai",
  coordinate: { lat: 31.2304, lng: 121.4737 },
  address: "Shanghai",
  category: "city",
  provider: "mapbox",
}

function fixtureMapProvider(
  name: MapProvider["name"],
  geocode: MapProvider["geocode"],
  ok = true
): MapProvider {
  return {
    name,
    async health() {
      return ok ? { ok: true } : { ok: false, reason: "fixture unhealthy" }
    },
    geocode,
    async reverseGeocode() {
      return geocode({ query: "reverse fixture" })
    },
    async searchPlaces() {
      return [await geocode({ query: "search fixture" })]
    },
    async route() {
      throw new Error("route fixture unused")
    },
  }
}

describe("provider registry", () => {
  it("routes China destinations to AMap by country code", async () => {
    const registry = createProviderRegistry({
      mapProviders: {
        amap: fixtureMapProvider("amap", async () => amapPlace),
        mapbox: fixtureMapProvider("mapbox", async () => mapboxPlace),
      },
    })

    const place = await registry.geocode({ countryCode: "CN", query: "Shanghai" })

    expect(place.provider).toBe("amap")
  })

  it("routes international destinations to Mapbox by country code even when the city name is Chinese", async () => {
    const registry = createProviderRegistry({
      mapProviders: {
        amap: fixtureMapProvider("amap", async () => amapPlace),
        mapbox: fixtureMapProvider("mapbox", async () => mapboxPlace),
      },
    })

    const place = await registry.geocode({ countryCode: "US", query: "北京" })

    expect(place.provider).toBe("mapbox")
  })

  it("falls back when the primary provider times out", async () => {
    const registry = createProviderRegistry({
      operationTimeoutMs: 1,
      mapProviders: {
        amap: fixtureMapProvider("amap", () => new Promise<NormalizedPlace>(() => undefined)),
        mapbox: fixtureMapProvider("mapbox", async () => mapboxPlace),
      },
    })

    const place = await registry.geocode({ countryCode: "CN", query: "Shanghai" })

    expect(place.provider).toBe("mapbox")
  })

  it("falls back when the primary provider returns an invalid normalized payload", async () => {
    const registry = createProviderRegistry({
      mapProviders: {
        amap: fixtureMapProvider("amap", async () => ({ ...amapPlace, coordinate: "31,121" }) as unknown as NormalizedPlace),
        mapbox: fixtureMapProvider("mapbox", async () => mapboxPlace),
      },
    })

    const place = await registry.geocode({ countryCode: "CN", query: "Shanghai" })

    expect(place.provider).toBe("mapbox")
  })

  it("returns a typed provider error when fallback also fails", async () => {
    const registry = createProviderRegistry({
      mapProviders: {
        amap: fixtureMapProvider("amap", async () => ({ ...amapPlace, coordinate: "31,121" }) as unknown as NormalizedPlace),
        mapbox: fixtureMapProvider("mapbox", async () => ({ ...mapboxPlace, coordinate: null, provider: "bad" }) as unknown as NormalizedPlace),
      },
    })

    await expect(registry.geocode({ countryCode: "CN", query: "Shanghai" })).rejects.toMatchObject({
      name: "ProviderRegistryError",
      code: "PROVIDER_FALLBACK_FAILED",
    })

    try {
      await registry.geocode({ countryCode: "CN", query: "Shanghai" })
    } catch (error) {
      expect(error).toBeInstanceOf(ProviderRegistryError)
      expect((error as ProviderRegistryError).attempts.map((attempt) => attempt.provider)).toEqual([
        "amap",
        "mapbox",
      ])
    }
  })
})
