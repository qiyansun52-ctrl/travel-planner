"use client"

import { useState } from "react"
import {
  hasDensityWarning,
  isContinueDisabled,
  normalizeSelectedCardIds,
} from "@/lib/selection"
import type { DiscoveryOutput, PlanningSession } from "@/lib/types"
import { AreaImpressionList } from "./AreaImpressionList"
import { BudgetBandPanel } from "./BudgetBandPanel"
import { DiscoveryCardGrid } from "./DiscoveryCardGrid"
import { FoodSummaryList } from "./FoodSummaryList"

interface DiscoveryBoardProps {
  session: PlanningSession
  output: DiscoveryOutput
  onSelectionChange: (selectedIds: string[]) => Promise<void> | void
  onContinue: (selectedIds: string[]) => Promise<void> | void
}

export function DiscoveryBoard({
  session,
  output,
  onSelectionChange,
  onContinue,
}: DiscoveryBoardProps) {
  const [selectedIds, setSelectedIds] = useState(
    session.discovery_state?.selected_card_ids ?? []
  )
  const [saving, setSaving] = useState(false)

  async function toggle(id: string) {
    const next = normalizeSelectedCardIds(
      selectedIds.includes(id)
        ? selectedIds.filter((selectedId) => selectedId !== id)
        : [...selectedIds, id]
    )
    setSelectedIds(next)
    setSaving(true)
    try {
      await onSelectionChange(next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[1fr_320px]">
      <main className="space-y-8">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
            {session.hard_constraints.destination_city}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            Choose what feels worth it
          </h1>
        </div>

        <DiscoveryCardGrid cards={output.cards} selectedIds={selectedIds} onToggle={toggle} />
        <FoodSummaryList items={output.food_summaries} />
        <AreaImpressionList items={output.area_summaries} />
      </main>

      <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <BudgetBandPanel budget={output.budget_estimate} />
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Selected</p>
          <p className="mt-1 text-3xl font-semibold text-slate-950">{selectedIds.length}</p>
          {hasDensityWarning(selectedIds.length, session.hard_constraints.duration_days) && (
            <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Density warning: this may be more than five stops per day.
            </p>
          )}
          <button
            type="button"
            disabled={isContinueDisabled(selectedIds) || saving}
            onClick={() => onContinue(selectedIds)}
            className="mt-4 h-11 w-full rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Continue to preferences
          </button>
        </div>
      </aside>
    </div>
  )
}
