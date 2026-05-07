import type { Coordinate } from "@/domain/schemas"

const PI = Math.PI
const EARTH_RADIUS = 6378245.0
const ECCENTRICITY_SQUARED = 0.00669342162296594323

export function convertGcj02ToWgs84(coordinate: Coordinate): Coordinate {
  if (isOutsideChina(coordinate)) {
    return { ...coordinate }
  }

  const delta = calculateGcjOffset(coordinate)
  const gcjLat = coordinate.lat + delta.lat
  const gcjLng = coordinate.lng + delta.lng

  return {
    lat: coordinate.lat * 2 - gcjLat,
    lng: coordinate.lng * 2 - gcjLng,
  }
}

export function isOutsideChina(coordinate: Coordinate): boolean {
  return (
    coordinate.lng < 72.004 ||
    coordinate.lng > 137.8347 ||
    coordinate.lat < 0.8293 ||
    coordinate.lat > 55.8271
  )
}

function calculateGcjOffset(coordinate: Coordinate): Coordinate {
  let dLat = transformLat(coordinate.lng - 105.0, coordinate.lat - 35.0)
  let dLng = transformLng(coordinate.lng - 105.0, coordinate.lat - 35.0)
  const radLat = (coordinate.lat / 180.0) * PI
  let magic = Math.sin(radLat)
  magic = 1 - ECCENTRICITY_SQUARED * magic * magic
  const sqrtMagic = Math.sqrt(magic)

  dLat =
    (dLat * 180.0) /
    (((EARTH_RADIUS * (1 - ECCENTRICITY_SQUARED)) / (magic * sqrtMagic)) * PI)
  dLng =
    (dLng * 180.0) /
    ((EARTH_RADIUS / sqrtMagic) * Math.cos(radLat) * PI)

  return { lat: dLat, lng: dLng }
}

function transformLat(x: number, y: number): number {
  let result = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y
  result += 0.2 * Math.sqrt(Math.abs(x))
  result += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0
  result += ((20.0 * Math.sin(y * PI) + 40.0 * Math.sin((y / 3.0) * PI)) * 2.0) / 3.0
  result +=
    ((160.0 * Math.sin((y / 12.0) * PI) + 320 * Math.sin((y * PI) / 30.0)) * 2.0) /
    3.0
  return result
}

function transformLng(x: number, y: number): number {
  let result = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y
  result += 0.1 * Math.sqrt(Math.abs(x))
  result += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0
  result += ((20.0 * Math.sin(x * PI) + 40.0 * Math.sin((x / 3.0) * PI)) * 2.0) / 3.0
  result +=
    ((150.0 * Math.sin((x / 12.0) * PI) + 300.0 * Math.sin((x / 30.0) * PI)) *
      2.0) /
    3.0
  return result
}
