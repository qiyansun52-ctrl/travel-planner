export * from "./generated/types"

export interface PlanningProgressEvent {
  stage: string
  status: "start" | "started" | "finish" | "completed" | "skipped" | "failed" | "error"
  message: string
  payload?: Record<string, unknown>
}
