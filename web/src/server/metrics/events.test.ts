import { mkdtemp, readFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { describe, expect, it } from "vitest"
import {
  appendMetricEvent,
  computeMetricSummary,
  safeAppendMetricEvent,
} from "./events"

describe("metrics events", () => {
  it("writes JSONL events and computes funnel totals", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "travel-metrics-"))
    const filePath = path.join(dir, "events.jsonl")

    await appendMetricEvent(
      { name: "step1_submitted", session_id: "s1", payload: {} },
      filePath
    )
    await appendMetricEvent(
      { name: "discovery_enrichment_summary", session_id: "s1", payload: { total_cards: 3 } },
      filePath
    )
    await appendMetricEvent(
      { name: "itinerary_finalized", session_id: "s1", payload: {} },
      filePath
    )

    const lines = (await readFile(filePath, "utf8")).trim().split("\n")
    expect(lines).toHaveLength(3)

    const summary = await computeMetricSummary(filePath)
    expect(summary.eventCounts.step1_submitted).toBe(1)
    expect(summary.eventCounts.itinerary_finalized).toBe(1)
    expect(summary.sessionsSubmitted).toBe(1)
    expect(summary.sessionsWithFinalItinerary).toBe(1)
  })

  it("swallows logging failures through the safe helper", async () => {
    await expect(
      safeAppendMetricEvent(
        { name: "step1_submitted", session_id: "s1", payload: {} },
        "/dev/null/events.jsonl"
      )
    ).resolves.toBeUndefined()
  })
})
