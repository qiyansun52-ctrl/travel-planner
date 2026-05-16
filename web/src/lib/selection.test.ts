import { describe, expect, it } from "vitest"
import {
  hasDensityWarning,
  isContinueDisabled,
  normalizeSelectedCardIds,
} from "./selection"

describe("selection helpers", () => {
  it("normalizes selected card ids without empty values or duplicates", () => {
    expect(normalizeSelectedCardIds(["card-a", "", "card-a", "card-b"])).toEqual([
      "card-a",
      "card-b",
    ])
  })

  it("blocks continuing with no selected cards", () => {
    expect(isContinueDisabled([])).toBe(true)
    expect(isContinueDisabled(["card-a"])).toBe(false)
  })

  it("warns when density is above five stops per day", () => {
    expect(hasDensityWarning(16, 3)).toBe(true)
    expect(hasDensityWarning(15, 3)).toBe(false)
  })
})
