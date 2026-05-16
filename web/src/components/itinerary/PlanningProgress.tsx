import type { PlanningProgressEvent } from "@/lib/types"

const STEPS = [
  { id: "stay", label: "住宿区域", icon: "🏨" },
  { id: "transport", label: "交通方案", icon: "🚇" },
  { id: "planner", label: "每日行程", icon: "📅" },
  { id: "validator", label: "预算校验", icon: "✅" },
] as const

type StepId = typeof STEPS[number]["id"]
type StepStatus = "pending" | "active" | "done" | "error"

function resolveStepStatus(
  stepId: StepId,
  events: PlanningProgressEvent[],
  activeStage: string | undefined,
  planning: boolean,
): StepStatus {
  const stepEvents = events.filter((event) => event.stage === stepId)
  const last = stepEvents.at(-1)
  if (last?.status === "finish" || last?.status === "completed") return "done"
  if (last?.status === "error" || last?.status === "failed") return "error"
  if (planning && activeStage === stepId) return "active"
  return "pending"
}

export function PlanningProgress({
  active,
  events = [],
}: {
  active: boolean
  events?: PlanningProgressEvent[]
}) {
  const latest = events.at(-1)
  const activeStage = active ? latest?.stage : undefined

  if (!active && events.length === 0) return null

  return (
    <section
      aria-label="规划进度"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
            AI 规划中
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            {active ? "正在为你生成行程…" : "规划完成"}
          </h2>
        </div>
        {active && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
            <SpinnerIcon />
            生成中
          </span>
        )}
      </div>

      <ol className="relative flex flex-col gap-4 sm:flex-row sm:gap-0">
        {STEPS.map((step, index) => {
          const status = resolveStepStatus(step.id, events, activeStage, active)
          const isLast = index === STEPS.length - 1

          return (
            <li
              key={step.id}
              className="flex flex-1 items-start gap-3 sm:flex-col sm:items-center sm:gap-2"
            >
              <div className="flex flex-col items-center sm:w-full sm:flex-row">
                <StepCircle status={status} icon={step.icon} />
                {!isLast && (
                  <div
                    className={`
                      mx-2 hidden h-0.5 flex-1 sm:block
                      ${status === "done" ? "bg-teal-400" : "bg-slate-200"}
                      transition-colors duration-500
                    `}
                  />
                )}
              </div>
              <div className="pt-0.5 sm:pt-2 sm:text-center">
                <p
                  className={`text-sm font-medium ${
                    status === "pending" ? "text-slate-400" : "text-slate-900"
                  }`}
                >
                  {step.label}
                </p>
              </div>
            </li>
          )
        })}
      </ol>

      {latest?.message && (
        <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-500">
          {latest.message}
        </p>
      )}
    </section>
  )
}

function StepCircle({ status, icon }: { status: StepStatus; icon: string }) {
  if (status === "done") {
    return (
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-teal-500 text-white shadow-sm">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M3 8l4 4 6-6"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2.5"
          />
        </svg>
      </span>
    )
  }

  if (status === "active") {
    return (
      <span className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-teal-200 opacity-75" />
        <span className="relative flex h-9 w-9 items-center justify-center rounded-full border-2 border-teal-500 bg-white text-base">
          {icon}
        </span>
      </span>
    )
  }

  if (status === "error") {
    return (
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border-2 border-red-400 bg-red-50 text-base">
        ✕
      </span>
    )
  }

  return (
    <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border-2 border-slate-200 bg-white text-base opacity-50">
      {icon}
    </span>
  )
}

function SpinnerIcon() {
  return (
    <svg
      className="animate-spin"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}
