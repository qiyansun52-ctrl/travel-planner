import { describe, expect, it } from "vitest"
import {
  hasDensityWarning,
  isContinueDisabled,
  normalizeSelectedCardIds,
} from "./selection"

describe("discovery selection helpers", () => {
  it("blocks continuing until at least one attraction card is selected", () => {
    expect(isContinueDisabled([])).toBe(true)
    expect(isContinueDisabled(["card_1"])).toBe(false)
  })

  it("warns only when selected cards exceed five stops per trip day", () => {
    expect(hasDensityWarning(10, 2)).toBe(false)
    expect(hasDensityWarning(11, 2)).toBe(true)
  })

  it("deduplicates selected ids while preserving first-seen order", () => {
    expect(normalizeSelectedCardIds(["a", "b", "a", "c", "b"])).toEqual([
      "a",
      "b",
      "c",
    ])
  })
})
