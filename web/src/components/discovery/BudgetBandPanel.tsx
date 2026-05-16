import type { BudgetSummary } from "@/lib/types"

export function BudgetBandPanel({ budget }: { budget: BudgetSummary }) {
  const rows = [
    ["交通", budget.transport],
    ["住宿", budget.stay],
    ["餐饮", budget.food],
    ["体验", budget.attractions],
    ["其他", budget.other],
    ["合计", budget.total],
  ] as const

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">发现阶段预算</h2>
      <div className="mt-3 space-y-2">
        {rows.map(([label, band]) => (
          <div key={label} className="flex items-center justify-between gap-4 text-sm">
            <span className="text-slate-500">{label}</span>
            <span className="font-medium text-slate-800">
              {band.currency} {Math.round(band.low)}-{Math.round(band.high)}
            </span>
          </div>
        ))}
      </div>
      {budget.total.high >= budget.user_budget && (
        <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          预算提醒：当前估算接近或超过你填写的总预算。
        </p>
      )}
    </aside>
  )
}
