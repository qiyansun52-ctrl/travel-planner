import type { BudgetSummary } from "@/lib/types"

export function BudgetBandPanel({ budget }: { budget: BudgetSummary }) {
  const rows = [
    ["Transport", budget.transport],
    ["Stay", budget.stay],
    ["Food", budget.food],
    ["Attractions", budget.attractions],
    ["Other", budget.other],
    ["Total", budget.total],
  ] as const

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Discovery budget</h2>
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
          Budget warning: estimate is near or above the stated trip budget.
        </p>
      )}
    </aside>
  )
}
