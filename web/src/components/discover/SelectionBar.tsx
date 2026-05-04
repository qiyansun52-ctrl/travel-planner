"use client"

import { useState, FormEvent } from "react"
import { AttractionCard, UserPreferences } from "@/lib/types"
import { Button } from "@/components/ui/Button"

interface SelectionBarProps {
  selected: AttractionCard[]
  destination: string
  budget: number
  onGenerate: (prefs: UserPreferences) => void
  generating: boolean
}

export function SelectionBar({
  selected,
  destination,
  budget,
  onGenerate,
  generating,
}: SelectionBarProps) {
  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState({
    departureCity: "",
    departureDate: "",
    days: 3,
    accommodationDescription: "",
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onGenerate({
      destination,
      departureCity: form.departureCity,
      departureDate: form.departureDate,
      days: form.days,
      totalBudget: budget,
      accommodationDescription: form.accommodationDescription,
      experienceDescription: selected.map((c) => c.name).join("、"),
    })
  }

  if (selected.length === 0) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50">
      {expanded ? (
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-gray-800">
              已选 {selected.length} 项 — 填写出行信息
            </p>
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">出发城市</label>
              <input
                required
                type="text"
                placeholder="例：北京"
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                value={form.departureCity}
                onChange={(e) => setForm({ ...form, departureCity: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">出发日期</label>
              <input
                required
                type="date"
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                value={form.departureDate}
                onChange={(e) => setForm({ ...form, departureDate: e.target.value })}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">旅行天数</label>
            <input
              required
              type="number"
              min={1}
              max={30}
              className="w-32 rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              value={form.days}
              onChange={(e) => setForm({ ...form, days: Number(e.target.value) })}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">
              住宿期待
              <span className="text-gray-400 font-normal ml-1">（可选）</span>
            </label>
            <textarea
              rows={2}
              placeholder="例：想住在老城区，有本地生活气息…"
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              value={form.accommodationDescription}
              onChange={(e) =>
                setForm({ ...form, accommodationDescription: e.target.value })
              }
            />
          </div>

          <Button type="submit" disabled={generating} className="w-full py-3 text-base">
            {generating ? "AI 正在规划中…" : "生成我的行程 →"}
          </Button>
        </form>
      ) : (
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <span className="font-semibold text-gray-900">已选 {selected.length} 项</span>
            <span className="text-gray-400 text-sm ml-2">
              {selected
                .slice(0, 3)
                .map((c) => c.name)
                .join("、")}
              {selected.length > 3 ? " 等" : ""}
            </span>
          </div>
          <Button onClick={() => setExpanded(true)}>继续规划 →</Button>
        </div>
      )}
    </div>
  )
}
