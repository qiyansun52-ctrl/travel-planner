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
          <p className="text-sm font-semibold uppercase text-teal-700">
            {session.hard_constraints.destination_city}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            选择真正值得去的体验
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            系统已把搜索线索、地图补全和预算信号整理成卡片。先选出最想保留的体验，下一步会据此安排住宿、交通和每日节奏。
          </p>
        </div>

        <DiscoveryCardGrid cards={output.cards} selectedIds={selectedIds} onToggle={toggle} />
        <FoodSummaryList items={output.food_summaries} />
        <AreaImpressionList items={output.area_summaries} />
      </main>

      <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <BudgetBandPanel budget={output.budget_estimate} />
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">已选择</p>
          <p className="mt-1 text-3xl font-semibold text-slate-950">{selectedIds.length}</p>
          {output.source_notes.length > 0 && (
            <p className="mt-2 text-sm leading-5 text-slate-600">
              已整理 {output.source_notes.length} 条搜索/地图线索。
            </p>
          )}
          {hasDensityWarning(selectedIds.length, session.hard_constraints.duration_days) && (
            <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              密度提醒：当前选择可能超过每天 5 个停留点，后续行程会偏满。
            </p>
          )}
          <button
            type="button"
            disabled={isContinueDisabled(selectedIds) || saving}
            onClick={() => onContinue(selectedIds)}
            className="mt-4 h-11 w-full rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            继续设置偏好
          </button>
        </div>
        <SourceNotes notes={output.source_notes} />
      </aside>
    </div>
  )
}

function SourceNotes({ notes }: { notes: DiscoveryOutput["source_notes"] }) {
  if (notes.length === 0) {
    return null
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">数据来源</h2>
      <ul className="mt-3 space-y-3">
        {notes.slice(0, 4).map((note, index) => (
          <li
            key={`${note.provider}-${note.url ?? index}`}
            className="border-t border-slate-200 pt-3 first:border-t-0 first:pt-0"
          >
            <p className="text-xs font-semibold uppercase text-slate-500">{note.provider}</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{note.note}</p>
            {note.url && (
              <a
                href={note.url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex text-sm font-semibold text-teal-700 hover:text-teal-900"
              >
                查看来源
              </a>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
