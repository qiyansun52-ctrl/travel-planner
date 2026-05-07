// @vitest-environment node

import { mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { FileSessionRepository } from "./fileSessionRepository"
import {
  BudgetBand,
  HardConstraints,
  Itinerary,
  Preference,
  ValidatorIssue,
} from "@/domain/schemas"

let tempDir: string
let repository: FileSessionRepository

const hardConstraints: HardConstraints = {
  departure_city: "Beijing",
  destination_city: "Shanghai",
  destination_country_code: "CN",
  departure_date: "2026-05-10",
  duration_days: 3,
  traveler_count: 2,
  total_budget: 5000,
  currency: "CNY",
}

const preferences: Preference = {
  area_vibe: "central and walkable",
  quiet_vs_lively: "balanced",
  stay_type: "hotel",
  willing_to_change_hotels: false,
  intercity_transport_preference: "rail",
  early_departure_tolerance: "medium",
  transfer_tolerance: "low",
  pay_more_to_save_time: true,
}

const band: BudgetBand = {
  currency: "CNY",
  low: 100,
  high: 200,
  confidence: "medium",
  basis: "per_trip",
}

const itinerary: Itinerary = {
  id: "itinerary_1",
  session_id: "session_placeholder",
  days: [],
  budget: {
    currency: "CNY",
    transport: band,
    stay: band,
    food: band,
    attractions: band,
    other: band,
    total: band,
    user_budget: 5000,
    overrun_flag: false,
  },
  validator_issues: [],
  version: 1,
}

const warningIssue: ValidatorIssue = {
  code: "DAY_OVERLOADED",
  severity: "warning",
  scope: { type: "day", day_index: 1 },
  message: "Day 1 may feel dense.",
  suggested_action: "Move one stop.",
}

beforeEach(async () => {
  tempDir = await mkdtemp(path.join(tmpdir(), "travel-session-repo-"))
  repository = new FileSessionRepository(path.join(tempDir, "sessions.json"))
})

afterEach(async () => {
  await rm(tempDir, { recursive: true, force: true })
})

describe("FileSessionRepository", () => {
  it("creates and retrieves an active session", async () => {
    const session = await repository.create(hardConstraints)

    expect(session.status).toBe("active")
    expect(session.hard_constraints).toEqual(hardConstraints)
    expect(session.discovery_state).toBeNull()
    await expect(repository.get(session.session_id)).resolves.toEqual(session)
  })

  it("writes discovery, preferences, itinerary, and conversation turns", async () => {
    const session = await repository.create(hardConstraints)

    await repository.updateDiscovery(session.session_id, {
      payload: null,
      selected_card_ids: ["card_1"],
    })
    await repository.updatePreferences(session.session_id, preferences)
    await repository.writeItinerary(
      session.session_id,
      { ...itinerary, session_id: session.session_id },
      [warningIssue]
    )
    const updated = await repository.appendConversationTurn(session.session_id, {
      id: "turn_1",
      raw_text: "Make day two easier.",
      classification: null,
      created_at: "2026-05-07T00:00:00.000Z",
    })

    expect(updated.discovery_state?.selected_card_ids).toEqual(["card_1"])
    expect(updated.preferences).toEqual(preferences)
    expect(updated.itinerary?.id).toBe("itinerary_1")
    expect(updated.validator_issues).toEqual([warningIssue])
    expect(updated.conversation_history).toHaveLength(1)
  })

  it("uses last-write-wins for repeated updates", async () => {
    const session = await repository.create(hardConstraints)

    await repository.updateDiscovery(session.session_id, {
      payload: null,
      selected_card_ids: ["old_card"],
    })
    const updated = await repository.updateDiscovery(session.session_id, {
      payload: null,
      selected_card_ids: ["new_card"],
    })

    expect(updated.discovery_state?.selected_card_ids).toEqual(["new_card"])
  })

  it("resetToStep clears downstream state and preserves the session id", async () => {
    const session = await repository.create(hardConstraints)
    await repository.updateDiscovery(session.session_id, {
      payload: null,
      selected_card_ids: ["card_1"],
    })
    await repository.updatePreferences(session.session_id, preferences)
    await repository.writeItinerary(
      session.session_id,
      { ...itinerary, session_id: session.session_id },
      [warningIssue]
    )

    const reset = await repository.resetToStep(session.session_id, "discovery", {
      ...hardConstraints,
      total_budget: 4500,
    })

    expect(reset.session_id).toBe(session.session_id)
    expect(reset.hard_constraints.total_budget).toBe(4500)
    expect(reset.discovery_state).toBeNull()
    expect(reset.preferences).toBeNull()
    expect(reset.itinerary).toBeNull()
    expect(reset.validator_issues).toEqual([])
  })

  it("archiveAndFork archives the original and returns a linked active session", async () => {
    const original = await repository.create(hardConstraints)
    const fork = await repository.archiveAndFork(original.session_id, "before budget cut", {
      ...hardConstraints,
      total_budget: 3000,
    })
    const archived = await repository.get(original.session_id)

    expect(archived?.status).toBe("archived")
    expect(archived?.snapshot_label).toBe("before budget cut")
    expect(fork.status).toBe("active")
    expect(fork.parent_session_id).toBe(original.session_id)
    expect(fork.hard_constraints.total_budget).toBe(3000)
  })

  it("rejects archived mutations except snapshot label updates", async () => {
    const original = await repository.create(hardConstraints)
    await repository.archiveAndFork(original.session_id, "snapshot", hardConstraints)

    await expect(
      repository.updatePreferences(original.session_id, preferences)
    ).rejects.toThrow(/archived/)

    const relabeled = await repository.updateSnapshotLabel(original.session_id, "final snapshot")

    expect(relabeled.snapshot_label).toBe("final snapshot")
  })
})
