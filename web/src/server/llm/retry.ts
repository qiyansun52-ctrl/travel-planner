export interface RetryOptions {
  maxRetries?: number
  baseDelayMs?: number
  maxDelayMs?: number
  shouldRetry?: (error: unknown) => boolean
}

export interface RetryResult<T> {
  value: T
  retryCount: number
}

export class RetryExhaustedError extends Error {
  readonly cause: unknown
  readonly retryCount: number

  constructor(error: unknown, retryCount: number) {
    super(error instanceof Error ? error.message : String(error))
    this.name = "RetryExhaustedError"
    this.cause = error
    this.retryCount = retryCount
  }
}

const DEFAULT_MAX_RETRIES = 2
const DEFAULT_BASE_DELAY_MS = 250
const DEFAULT_MAX_DELAY_MS = 2_000

export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {}
): Promise<RetryResult<T>> {
  const maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES
  const baseDelayMs = options.baseDelayMs ?? DEFAULT_BASE_DELAY_MS
  const maxDelayMs = options.maxDelayMs ?? DEFAULT_MAX_DELAY_MS
  const shouldRetry = options.shouldRetry ?? isTransientNetworkError
  let retryCount = 0

  while (true) {
    try {
      return {
        value: await operation(),
        retryCount,
      }
    } catch (error) {
      if (retryCount >= maxRetries || !shouldRetry(error)) {
        throw new RetryExhaustedError(error, retryCount)
      }

      const delayMs = Math.min(baseDelayMs * 2 ** retryCount, maxDelayMs)
      retryCount += 1
      await delay(delayMs)
    }
  }
}

export function isTransientNetworkError(error: unknown): boolean {
  if (error instanceof TypeError) return true

  if (!error || typeof error !== "object") return false
  const maybeError = error as {
    code?: string
    retryable?: boolean
    transient?: boolean
    status?: number
  }

  if (maybeError.retryable || maybeError.transient) return true
  if (maybeError.status === 408 || maybeError.status === 429) return true
  if (typeof maybeError.status === "number" && maybeError.status >= 500) return true

  return [
    "ECONNRESET",
    "ECONNREFUSED",
    "EHOSTUNREACH",
    "ENETUNREACH",
    "ETIMEDOUT",
    "EAI_AGAIN",
  ].includes(maybeError.code ?? "")
}

function delay(ms: number): Promise<void> {
  if (ms <= 0) return Promise.resolve()
  return new Promise((resolve) => setTimeout(resolve, ms))
}
