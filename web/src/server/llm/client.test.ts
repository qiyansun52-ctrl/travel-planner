// @vitest-environment node

import { describe, expect, it, vi } from "vitest"
import { z } from "zod"
import { callLLM, LLMProvider } from "./client"
import { LLMCostLogEntry } from "./costLogger"

const outputSchema = z
  .object({
    message: z.string(),
  })
  .strict()

const noopCostLogger = () => undefined

function fixtureProvider(
  handler: LLMProvider["generate"]
): LLMProvider & { generate: ReturnType<typeof vi.fn<LLMProvider["generate"]>> } {
  return {
    generate: vi.fn(handler),
  }
}

describe("callLLM", () => {
  it("returns output parsed and validated against the provided schema", async () => {
    const entries: LLMCostLogEntry[] = []
    const provider = fixtureProvider(async () => '{"message":"hello"}')

    const result = await callLLM({
      system: "You return JSON.",
      user: "Say hello.",
      schema: outputSchema,
      label: "unit.success",
      provider,
      costLogger: (entry) => {
        entries.push(entry)
      },
      retry: { baseDelayMs: 0 },
    })

    expect(result).toEqual({ message: "hello" })
    expect(provider.generate).toHaveBeenCalledTimes(1)
    expect(entries).toHaveLength(1)
    expect(entries[0]).toMatchObject({
      label: "unit.success",
      success: true,
      retry_count: 0,
    })
    expect(entries[0].prompt_tokens_estimate).toBeGreaterThan(0)
    expect(entries[0].completion_tokens_estimate).toBeGreaterThan(0)
    expect(entries[0].duration_ms).toBeGreaterThanOrEqual(0)
  })

  it("repairs malformed JSON before schema validation", async () => {
    const provider = fixtureProvider(async () => 'Sure:\n{"message":"hello",}\n')

    await expect(
      callLLM({
        system: "You return JSON.",
        user: "Say hello.",
        schema: outputSchema,
        label: "unit.repair",
        provider,
        costLogger: noopCostLogger,
        retry: { baseDelayMs: 0 },
      })
    ).resolves.toEqual({ message: "hello" })
  })

  it("retries transient network failures before returning validated output", async () => {
    const entries: LLMCostLogEntry[] = []
    const provider = fixtureProvider(
      vi
        .fn()
        .mockRejectedValueOnce(new TypeError("fetch failed"))
        .mockResolvedValueOnce('{"message":"recovered"}')
    )

    const result = await callLLM({
      system: "You return JSON.",
      user: "Recover.",
      schema: outputSchema,
      label: "unit.retry",
      provider,
      costLogger: (entry) => {
        entries.push(entry)
      },
      retry: { baseDelayMs: 0 },
    })

    expect(result).toEqual({ message: "recovered" })
    expect(provider.generate).toHaveBeenCalledTimes(2)
    expect(entries[0]).toMatchObject({
      success: true,
      retry_count: 1,
    })
  })

  it("enforces the configured timeout", async () => {
    const provider = fixtureProvider(() => new Promise<string>(() => undefined))

    await expect(
      callLLM({
        system: "You return JSON.",
        user: "Hang forever.",
        schema: outputSchema,
        label: "unit.timeout",
        timeoutMs: 5,
        provider,
        costLogger: noopCostLogger,
        retry: { baseDelayMs: 0 },
      })
    ).rejects.toMatchObject({ name: "LLMTimeoutError" })

    expect(provider.generate).toHaveBeenCalledTimes(1)
  })

  it("does not fail the LLM call when cost logging throws", async () => {
    const provider = fixtureProvider(async () => '{"message":"hello"}')

    await expect(
      callLLM({
        system: "You return JSON.",
        user: "Say hello.",
        schema: outputSchema,
        label: "unit.logging_failure",
        provider,
        costLogger: () => {
          throw new Error("disk full")
        },
        retry: { baseDelayMs: 0 },
      })
    ).resolves.toEqual({ message: "hello" })
  })
})
