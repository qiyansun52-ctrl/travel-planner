import { z } from "zod"
import { createLLMCostLogEntry, LLMCostLogger, logLLMCost } from "./costLogger"
import { parseJsonWithRepair } from "./jsonRepair"
import { RetryExhaustedError, RetryOptions, withRetry } from "./retry"

const DEFAULT_TIMEOUT_MS = 30_000
const DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
const GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com"

export interface LLMProviderInput {
  system: string
  user: string
  signal: AbortSignal
}

export interface LLMProvider {
  generate(input: LLMProviderInput): Promise<string>
}

export interface CallLLMInput<TSchema extends z.ZodType> {
  system: string
  user: string
  schema: TSchema
  label: string
  timeoutMs?: number
  provider?: LLMProvider
  costLogger?: LLMCostLogger
  retry?: RetryOptions
}

interface GeminiProviderOptions {
  apiKey?: string
  model?: string
  fetcher?: typeof fetch
  baseUrl?: string
}

interface GeminiGenerateContentResponse {
  candidates?: Array<{
    content?: {
      parts?: Array<{
        text?: string
      }>
    }
  }>
  error?: {
    code?: number
    message?: string
    status?: string
  }
}

export class LLMConfigurationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "LLMConfigurationError"
  }
}

export class LLMNetworkError extends Error {
  readonly cause: unknown
  readonly transient = true
  readonly retryable = true
  readonly status: number | undefined

  constructor(message: string, cause?: unknown, status?: number) {
    super(message)
    this.name = "LLMNetworkError"
    this.cause = cause
    this.status = status
  }
}

export class LLMAuthError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "LLMAuthError"
  }
}

export class LLMProviderError extends Error {
  readonly status: number | undefined

  constructor(message: string, status?: number) {
    super(message)
    this.name = "LLMProviderError"
    this.status = status
  }
}

export class LLMTimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`LLM call timed out after ${timeoutMs}ms`)
    this.name = "LLMTimeoutError"
  }
}

export class LLMJsonParseError extends Error {
  readonly cause: unknown

  constructor(message: string, cause: unknown) {
    super(message)
    this.name = "LLMJsonParseError"
    this.cause = cause
  }
}

export async function callLLM<TSchema extends z.ZodType>(
  input: CallLLMInput<TSchema>
): Promise<z.infer<TSchema>> {
  const provider = input.provider ?? createDefaultLLMProvider()
  const logger = input.costLogger ?? logLLMCost
  const timeoutMs = input.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const startedAt = Date.now()
  let completion = ""
  let retryCount = 0
  let success = false
  let failure: string | null = null

  try {
    const result = await withRetry(
      () =>
        withTimeout(
          (signal) =>
            provider.generate({
              system: input.system,
              user: input.user,
              signal,
            }),
          timeoutMs
        ),
      input.retry
    )

    completion = result.value
    retryCount = result.retryCount
    const parsed = parseLLMJson(completion)
    const validated = input.schema.parse(parsed)
    success = true
    return validated
  } catch (error) {
    const unwrapped = unwrapRetryError(error)
    if (error instanceof RetryExhaustedError) {
      retryCount = error.retryCount
    }
    failure = errorMessage(unwrapped)
    throw unwrapped
  } finally {
    safeLogCost(logger, {
      label: input.label,
      system: input.system,
      user: input.user,
      completion,
      durationMs: Date.now() - startedAt,
      success,
      failure,
      retryCount,
    })
  }
}

export function createDefaultLLMProvider(
  env: NodeJS.ProcessEnv = process.env
): LLMProvider {
  return new GeminiLLMProvider({
    apiKey: readLLMProviderApiKey(env),
    model: env.LLM_PROVIDER_MODEL ?? env.GEMINI_MODEL ?? DEFAULT_GEMINI_MODEL,
  })
}

export function readLLMProviderApiKey(env: NodeJS.ProcessEnv = process.env): string {
  const apiKey = env.LLM_PROVIDER_API_KEY ?? env.GEMINI_API_KEY
  if (!apiKey) {
    throw new LLMConfigurationError("LLM_PROVIDER_API_KEY is not configured")
  }

  return apiKey
}

export class GeminiLLMProvider implements LLMProvider {
  private readonly apiKey: string | undefined
  private readonly model: string
  private readonly fetcher: typeof fetch
  private readonly baseUrl: string

  constructor(options: GeminiProviderOptions = {}) {
    this.apiKey = options.apiKey
    this.model = options.model ?? DEFAULT_GEMINI_MODEL
    this.fetcher = options.fetcher ?? fetch
    this.baseUrl = options.baseUrl ?? GEMINI_API_BASE_URL
  }

  async generate(input: LLMProviderInput): Promise<string> {
    const apiKey = this.requireApiKey()
    const url = new URL(`/v1beta/models/${this.model}:generateContent`, this.baseUrl)
    url.searchParams.set("key", apiKey)

    let response: Response
    try {
      response = await this.fetcher(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          systemInstruction: {
            parts: [{ text: input.system }],
          },
          contents: [
            {
              role: "user",
              parts: [{ text: input.user }],
            },
          ],
          generationConfig: {
            responseMimeType: "application/json",
          },
        }),
        signal: input.signal,
      })
    } catch (error) {
      if (isAbortError(error)) throw error
      throw new LLMNetworkError("LLM provider network failure", error)
    }

    const body = (await response.json().catch(() => ({}))) as GeminiGenerateContentResponse
    if (response.status === 401 || response.status === 403) {
      throw new LLMAuthError(body.error?.message ?? "LLM provider authentication failed")
    }

    if (response.status === 408 || response.status === 429 || response.status >= 500) {
      throw new LLMNetworkError(
        body.error?.message ?? `LLM provider transient HTTP ${response.status}`,
        body,
        response.status
      )
    }

    if (!response.ok) {
      throw new LLMProviderError(
        body.error?.message ?? `LLM provider HTTP ${response.status}`,
        response.status
      )
    }

    const text = body.candidates?.[0]?.content?.parts
      ?.map((part) => part.text ?? "")
      .join("")
      .trim()

    if (!text) {
      throw new LLMProviderError("LLM provider returned no text")
    }

    return text
  }

  private requireApiKey(): string {
    if (!this.apiKey) {
      throw new LLMConfigurationError("LLM_PROVIDER_API_KEY is not configured")
    }

    return this.apiKey
  }
}

function parseLLMJson(completion: string): unknown {
  try {
    return JSON.parse(completion) as unknown
  } catch (initialError) {
    try {
      return parseJsonWithRepair(completion)
    } catch (repairError) {
      throw new LLMJsonParseError("LLM returned invalid JSON", {
        initialError,
        repairError,
      })
    }
  }
}

async function withTimeout<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number
): Promise<T> {
  const controller = new AbortController()
  let timeoutHandle: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timeoutHandle = setTimeout(() => {
      const error = new LLMTimeoutError(timeoutMs)
      reject(error)
      controller.abort(error)
    }, timeoutMs)
  })

  try {
    return await Promise.race([operation(controller.signal), timeout])
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle)
  }
}

function unwrapRetryError(error: unknown): unknown {
  if (error instanceof RetryExhaustedError) return error.cause
  return error
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function safeLogCost(
  logger: LLMCostLogger,
  input: Parameters<typeof createLLMCostLogEntry>[0]
): void {
  const entry = createLLMCostLogEntry(input)
  try {
    void Promise.resolve(logger(entry)).catch(() => undefined)
  } catch {
    // Cost logging must never affect the user-facing LLM call.
  }
}

function isAbortError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false
  return (error as { name?: string }).name === "AbortError"
}
