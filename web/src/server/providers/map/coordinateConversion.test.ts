// @vitest-environment node

import { describe, expect, it } from "vitest"
import { normalizeAMapPlace } from "./amap"
import { convertGcj02ToWgs84 } from "./coordinateConversion"

describe("GCJ02 coordinate conversion", () => {
  it("keeps coordinates outside China unchanged", () => {
    const coordinate = { lat: 40.7128, lng: -74.006 }

    expect(convertGcj02ToWgs84(coordinate)).toEqual(coordinate)
  })

  it("converts China GCJ02 coordinates into nearby WGS84 coordinates", () => {
    const gcj02 = { lat: 31.2304, lng: 121.4737 }
    const wgs84 = convertGcj02ToWgs84(gcj02)

    expect(Math.abs(wgs84.lat - gcj02.lat)).toBeGreaterThan(0.001)
    expect(Math.abs(wgs84.lng - gcj02.lng)).toBeGreaterThan(0.001)
    expect(wgs84.lat).toBeGreaterThan(31)
    expect(wgs84.lat).toBeLessThan(32)
    expect(wgs84.lng).toBeGreaterThan(121)
    expect(wgs84.lng).toBeLessThan(122)
  })
})

describe("AMap place normalization", () => {
  it("does not expose raw GCJ02 coordinates as normalized coordinates", () => {
    const rawLocation = { lat: 31.2304, lng: 121.4737 }
    const place = normalizeAMapPlace({
      id: "B0FFG123",
      name: "人民广场",
      address: "上海市黄浦区",
      category: "landmark",
      location: `${rawLocation.lng},${rawLocation.lat}`,
    })

    expect(place.provider).toBe("amap")
    expect(place.id).toBe("amap:B0FFG123")
    expect(place.coordinate).not.toEqual(rawLocation)
    expect(place.coordinate?.lat).not.toBe(rawLocation.lat)
    expect(place.coordinate?.lng).not.toBe(rawLocation.lng)
  })
})
