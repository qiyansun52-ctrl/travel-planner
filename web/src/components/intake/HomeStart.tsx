"use client"

import { useEffect, useState } from "react"
import { listSessions } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"
import { HardConstraintForm, type IntakeLanguage } from "./HardConstraintForm"
import { RecentTrips } from "./RecentTrips"

const copy = {
  en: {
    eyebrow: "Single-city travel planning",
    title: "Plan a trip that actually fits you.",
    body: "Tell us your constraints. We'll find what's worth doing, then build a full itinerary around it.",
    switchLabel: "切换到中文",
    switchText: "中文",
  },
  zh: {
    eyebrow: "AI 单城市旅行规划",
    title: "一次真正适合你的旅行。",
    body: "锁定时间、预算和人数，AI 筛选值得去的体验，然后生成住宿、交通和每日行程。",
    switchLabel: "Switch to English",
    switchText: "EN",
  },
} satisfies Record<IntakeLanguage, Record<string, string>>

export function HomeStart() {
  const [language, setLanguage] = useState<IntakeLanguage>("zh")
  const [recentSessions, setRecentSessions] = useState<PlanningSession[]>([])
  const text = copy[language]

  useEffect(() => {
    let active = true
    listSessions()
      .then((sessions) => {
        if (active) setRecentSessions(sessions)
      })
      .catch(() => {
        if (active) setRecentSessions([])
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-slate-950 px-5 py-14 sm:px-10 lg:px-16">
        <div className="mx-auto grid max-w-5xl gap-10 lg:grid-cols-[1fr_420px] lg:items-start lg:gap-16">
          <div className="text-white">
            <button
              type="button"
              aria-label={text.switchLabel}
              onClick={() => setLanguage((current) => (current === "zh" ? "en" : "zh"))}
              className="mb-6 rounded-full border border-white/20 px-3 py-1 text-xs text-white/60 transition-colors hover:text-white/90"
            >
              {text.switchText}
            </button>
            <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">
              {text.eyebrow}
            </p>
            <h1 className="mt-4 max-w-md text-4xl font-bold leading-tight sm:text-5xl">
              {text.title}
            </h1>
            <p className="mt-5 max-w-sm text-base leading-7 text-slate-300">
              {text.body}
            </p>
            <div className="mt-8 flex flex-wrap gap-4 text-sm text-slate-400">
              <span>📍 单城市深度</span>
              <span>AI 多 agent 规划</span>
              <span>对话式调整</span>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm sm:p-6">
            <HardConstraintForm language={language} />
          </div>
        </div>
      </div>

      {recentSessions.length > 0 && (
        <div className="mx-auto max-w-5xl px-5 py-10 sm:px-10 lg:px-16">
          <RecentTrips sessions={recentSessions} language={language} />
        </div>
      )}
    </div>
  )
}
