export class JsonRepairError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "JsonRepairError"
  }
}

export function repairJson(input: string): string {
  const candidate = extractJsonCandidate(input)
  return candidate.replace(/,\s*([}\]])/g, "$1")
}

export function parseJsonWithRepair(input: string): unknown {
  return JSON.parse(repairJson(input)) as unknown
}

export function extractJsonCandidate(input: string): string {
  const start = findFirstJsonStart(input)
  if (start === -1) {
    throw new JsonRepairError("No JSON payload found in LLM output")
  }

  const end = findBalancedJsonEnd(input, start)
  if (end === -1) {
    throw new JsonRepairError("No complete JSON payload found in LLM output")
  }

  return input.slice(start, end + 1).trim()
}

function findFirstJsonStart(input: string): number {
  const objectStart = input.indexOf("{")
  const arrayStart = input.indexOf("[")

  if (objectStart === -1) return arrayStart
  if (arrayStart === -1) return objectStart
  return Math.min(objectStart, arrayStart)
}

function findBalancedJsonEnd(input: string, start: number): number {
  const stack: string[] = []
  let inString = false
  let escaped = false

  for (let i = start; i < input.length; i += 1) {
    const char = input[i]

    if (inString) {
      if (escaped) {
        escaped = false
      } else if (char === "\\") {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
      continue
    }

    if (char === '"') {
      inString = true
      continue
    }

    if (char === "{") {
      stack.push("}")
      continue
    }

    if (char === "[") {
      stack.push("]")
      continue
    }

    if (char === "}" || char === "]") {
      const expected = stack.pop()
      if (expected !== char) {
        throw new JsonRepairError("Mismatched JSON delimiters in LLM output")
      }

      if (stack.length === 0) return i
    }
  }

  return -1
}
