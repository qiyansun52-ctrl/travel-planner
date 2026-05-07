// @vitest-environment node

import { describe, expect, it } from "vitest"
import { parseJsonWithRepair, repairJson } from "./jsonRepair"

describe("repairJson", () => {
  it("strips leading and trailing non-JSON text", () => {
    const repaired = repairJson('Here is the payload:\n{"ok":true}\nDone.')

    expect(repaired).toBe('{"ok":true}')
  })

  it("fixes common trailing comma issues", () => {
    const parsed = parseJsonWithRepair(`{
      "items": [
        { "name": "Bund", },
      ],
    }`)

    expect(parsed).toEqual({ items: [{ name: "Bund" }] })
  })

  it("throws when no JSON payload can be found", () => {
    expect(() => repairJson("no structured payload")).toThrow(/No JSON payload/)
  })
})
