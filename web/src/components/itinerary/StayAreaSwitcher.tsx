"use client"

import { useState } from "react"
import { StayOption, StayRecommendation } from "@/domain/schemas"

interface StayAreaSwitcherProps {
  stay: StayRecommendation
  onSelect: (stayOptionId: string | null) => Promise<void> | void
}

function activeStayOption(stay: StayRecommendation): StayOption {
  const options = [stay.primary, ...stay.alternatives]
  return options.find((option) => option.id === stay.user_override_id) ?? stay.primary
}

export function StayAreaSwitcher({ stay, onSelect }: StayAreaSwitcherProps) {
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const active = activeStayOption(stay)
  const options = [stay.primary, ...stay.alternatives]

  async function choose(id: string | null) {
    setSaving(true)
    try {
      await onSelect(id)
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">Stay area</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">{active.area.name}</h2>
          <p className="mt-1 text-sm text-slate-600">{active.fit_reason}</p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
        >
          Change area
        </button>
      </div>

      {open && (
        <div className="mt-4 space-y-2">
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              disabled={saving}
              onClick={() => choose(option.id)}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                active.id === option.id
                  ? "border-slate-950 bg-slate-50"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              <span className="font-semibold text-slate-950">{option.area.name}</span>
              <span className="mt-1 block text-slate-600">{option.fit_reason}</span>
            </button>
          ))}
          <button
            type="button"
            disabled={saving}
            onClick={() => choose(null)}
            className="h-9 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            Reset to recommended
          </button>
        </div>
      )}
    </section>
  )
}
