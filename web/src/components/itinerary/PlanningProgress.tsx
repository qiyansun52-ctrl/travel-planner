import type { PlanningProgressEvent } from "@/lib/types"

export function PlanningProgress({
  active,
  events = [],
}: {
  active: boolean
  events?: PlanningProgressEvent[]
}) {
  const latest = events.at(-1)
  const steps = [
    { id: "stay", label: "推荐住宿区域" },
    { id: "transport", label: "分析交通方案" },
    { id: "planner", label: "生成每日行程" },
    { id: "validator", label: "检查预算与节奏" },
  ]

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">规划进度</h2>
          {latest && <p className="mt-1 text-sm text-slate-600">{latest.message}</p>}
        </div>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
          {active ? "生成中" : "待命"}
        </span>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-4">
        {steps.map((step) => {
          const matching = events.findLast((event) => event.stage === step.id)
          const isCurrent = latest?.stage === step.id && active
          return (
            <div
              key={step.id}
              className={`rounded-md px-3 py-2 text-sm ${
                isCurrent
                  ? "bg-sky-50 text-sky-900"
                  : matching?.status === "finish"
                    ? "bg-emerald-50 text-emerald-900"
                    : "bg-slate-50 text-slate-600"
              }`}
            >
              <span className="block font-medium">{step.label}</span>
              {matching && (
                <span className="mt-1 block text-xs">{formatStatus(matching.status)}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function formatStatus(status: PlanningProgressEvent["status"]): string {
  const labels: Record<PlanningProgressEvent["status"], string> = {
    completed: "已完成",
    error: "出错",
    failed: "失败",
    finish: "完成",
    skipped: "已跳过",
    start: "开始",
    started: "已开始",
  }
  return labels[status]
}
