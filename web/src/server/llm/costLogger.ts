import { appendFile, mkdir } from "node:fs/promises"
import path from "node:path"

export interface LLMCostLogEntry {
  timestamp: string
  label: string
  prompt_tokens_estimate: number
  completion_tokens_estimate: number
  duration_ms: number
  success: boolean
  failure: string | null
  retry_count: number
}

export type LLMCostLogger = (entry: LLMCostLogEntry) => void | Promise<void>

export function estimateTokenCount(text: string): number {
  const trimmed = text.trim()
  if (!trimmed) return 0
  return Math.max(1, Math.ceil(trimmed.length / 4))
}

export function createLLMCostLogEntry(input: {
  label: string
  system: string
  user: string
  completion: string
  durationMs: number
  success: boolean
  failure: string | null
  retryCount: number
}): LLMCostLogEntry {
  return {
    timestamp: new Date().toISOString(),
    label: input.label,
    prompt_tokens_estimate: estimateTokenCount(`${input.system}\n\n${input.user}`),
    completion_tokens_estimate: estimateTokenCount(input.completion),
    duration_ms: input.durationMs,
    success: input.success,
    failure: input.failure,
    retry_count: input.retryCount,
  }
}

export function logLLMCost(entry: LLMCostLogEntry, filePath = defaultLLMCostLogPath()): void {
  void appendCostLog(entry, filePath).catch(() => undefined)
}

export function defaultLLMCostLogPath(cwd = process.cwd()): string {
  return path.join(cwd, ".data", "llm-cost.jsonl")
}

async function appendCostLog(entry: LLMCostLogEntry, filePath: string): Promise<void> {
  await mkdir(path.dirname(filePath), { recursive: true })
  await appendFile(filePath, `${JSON.stringify(entry)}\n`, "utf8")
}
