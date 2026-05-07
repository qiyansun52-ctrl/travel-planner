import { describe, expect, it } from "vitest"
import { isChinaDestination } from "./geography"

describe("geography utilities", () => {
  it("treats only strict CN country codes as China destinations", () => {
    expect(isChinaDestination("CN")).toBe(true)
    expect(isChinaDestination("cn")).toBe(false)
    expect(isChinaDestination("CHN")).toBe(false)
    expect(isChinaDestination("US")).toBe(false)
  })
})
